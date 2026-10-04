import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.trustdesk.storage.database import get_db
from src.trustdesk.storage.repository import Repository
from src.trustdesk.ai import get_ai_provider
from src.trustdesk.orchestrator import SupportOperationsOrchestrator
from src.trustdesk.config import settings
from src.trustdesk.models.domain import (
    Customer,
    Order,
    KnowledgeDocument,
    Ticket,
    TicketCreate,
    DraftResponse,
    OperationalAction,
    AuditTrace,
    TicketStatusEnum,
)
from src.trustdesk.eval.runner import EvalRunner
from src.trustdesk.eval.metrics import EvalSummary

router = APIRouter(prefix="/api")

@router.get("/health")
def health():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.version,
        "ai_provider": settings.ai_provider,
    }

# Customers
@router.get("/customers", response_model=List[Customer])
def list_customers(db: Session = Depends(get_db)):
    repo = Repository(db)
    return repo.list_customers()

# Orders
@router.get("/orders", response_model=List[Order])
def list_orders(customer_id: Optional[str] = None, db: Session = Depends(get_db)):
    repo = Repository(db)
    return repo.list_orders(customer_id=customer_id)

# Knowledge Base
@router.get("/kb", response_model=List[KnowledgeDocument])
def list_kb(active_only: bool = True, db: Session = Depends(get_db)):
    repo = Repository(db)
    return repo.list_kb_documents(active_only=active_only)

# Tickets
@router.get("/tickets", response_model=List[Ticket])
def list_tickets(status: Optional[str] = None, db: Session = Depends(get_db)):
    repo = Repository(db)
    return repo.list_tickets(status=status)

@router.post("/tickets", response_model=Ticket)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)):
    repo = Repository(db)
    from datetime import datetime
    ticket_id = f"TCK-{uuid.uuid4().hex[:6].upper()}"
    created_at = payload.created_at or (datetime.utcnow().isoformat() + "Z")
    ticket = Ticket(
        id=ticket_id,
        customer_id=payload.customer_id,
        order_id=payload.order_id,
        subject=payload.subject,
        description=payload.description,
        created_at=created_at,
        status=TicketStatusEnum.NEW,
    )
    return repo.create_ticket(ticket)

@router.get("/tickets/{ticket_id}")
def get_ticket_detail(ticket_id: str, db: Session = Depends(get_db)):
    repo = Repository(db)
    ticket = repo.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    customer = repo.get_customer(ticket.customer_id) if ticket.customer_id else None
    order = repo.get_order(ticket.order_id) if ticket.order_id else None
    draft = repo.get_latest_draft(ticket_id)
    actions = repo.list_actions(ticket_id=ticket_id)
    traces = repo.list_audit_traces(ticket_id=ticket_id)

    return {
        "ticket": ticket,
        "customer": customer,
        "order": order,
        "draft": draft,
        "actions": actions,
        "traces": traces,
    }

@router.post("/tickets/{ticket_id}/process")
async def process_ticket(ticket_id: str, db: Session = Depends(get_db)):
    repo = Repository(db)
    ticket = repo.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ai_provider = get_ai_provider(settings.ai_provider)
    orchestrator = SupportOperationsOrchestrator(ai_provider, repo)
    result = await orchestrator.process_ticket(ticket)
    return result

# Actions (HITL)
@router.get("/actions", response_model=List[OperationalAction])
def list_actions(status: Optional[str] = None, ticket_id: Optional[str] = None, db: Session = Depends(get_db)):
    repo = Repository(db)
    return repo.list_actions(status=status, ticket_id=ticket_id)

@router.post("/actions/{action_id}/approve")
def approve_action(action_id: str, db: Session = Depends(get_db)):
    repo = Repository(db)
    ai_provider = get_ai_provider(settings.ai_provider)
    orchestrator = SupportOperationsOrchestrator(ai_provider, repo)
    success, msg, action = orchestrator.action_executor.approve_action(action_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg, "action": action}

@router.post("/actions/{action_id}/reject")
def reject_action(action_id: str, reason: str = "Rejected by agent", db: Session = Depends(get_db)):
    repo = Repository(db)
    ai_provider = get_ai_provider(settings.ai_provider)
    orchestrator = SupportOperationsOrchestrator(ai_provider, repo)
    success, msg, action = orchestrator.action_executor.reject_action(action_id, reason=reason)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg, "action": action}

# Traces
@router.get("/traces", response_model=List[AuditTrace])
def list_traces(ticket_id: Optional[str] = None, db: Session = Depends(get_db)):
    repo = Repository(db)
    return repo.list_audit_traces(ticket_id=ticket_id)

# Benchmark Evaluation Run
@router.post("/eval/run", response_model=EvalSummary)
async def run_eval_benchmark():
    runner = EvalRunner()
    summary = await runner.run_benchmark()
    return summary
