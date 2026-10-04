import json
from enum import Enum
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from src.trustdesk.models.db_models import (
    CustomerModel,
    OrderModel,
    KnowledgeDocumentModel,
    TicketModel,
    DraftModel,
    OperationalActionModel,
    AuditTraceModel,
)
from src.trustdesk.models.domain import (
    Customer,
    Order,
    OrderItem,
    KnowledgeDocument,
    Ticket,
    DraftResponse,
    OperationalAction,
    AuditTrace,
    TicketStatusEnum,
    CategoryEnum,
    PriorityEnum,
    ActionTypeEnum,
    ActionStatusEnum,
)

class Repository:
    def __init__(self, db: Session):
        self.db = db

    # Customer
    def get_customer(self, customer_id: str) -> Optional[Customer]:
        m = self.db.query(CustomerModel).filter(CustomerModel.id == customer_id).first()
        if not m:
            return None
        return Customer(id=m.id, name=m.name, email=m.email, tier=m.tier, created_at=m.created_at)

    def list_customers(self) -> List[Customer]:
        rows = self.db.query(CustomerModel).all()
        return [Customer(id=m.id, name=m.name, email=m.email, tier=m.tier, created_at=m.created_at) for m in rows]

    # Order
    def get_order(self, order_id: str) -> Optional[Order]:
        m = self.db.query(OrderModel).filter(OrderModel.id == order_id).first()
        if not m:
            return None
        items_data = json.loads(m.items_json) if m.items_json else []
        items = [OrderItem(**i) for i in items_data]
        return Order(
            id=m.id,
            customer_id=m.customer_id,
            items=items,
            total_amount=m.total_amount,
            status=m.status,
            order_date=m.order_date,
            delivered_date=m.delivered_date,
            tracking_number=m.tracking_number,
        )

    def list_orders(self, customer_id: Optional[str] = None) -> List[Order]:
        q = self.db.query(OrderModel)
        if customer_id:
            q = q.filter(OrderModel.customer_id == customer_id)
        results = []
        for m in q.all():
            items_data = json.loads(m.items_json) if m.items_json else []
            results.append(Order(
                id=m.id,
                customer_id=m.customer_id,
                items=[OrderItem(**i) for i in items_data],
                total_amount=m.total_amount,
                status=m.status,
                order_date=m.order_date,
                delivered_date=m.delivered_date,
                tracking_number=m.tracking_number,
            ))
        return results

    # KB
    def get_kb_document(self, doc_id: str) -> Optional[KnowledgeDocument]:
        m = self.db.query(KnowledgeDocumentModel).filter(KnowledgeDocumentModel.doc_id == doc_id).first()
        if not m:
            return None
        tags = json.loads(m.tags_json) if m.tags_json else []
        return KnowledgeDocument(
            doc_id=m.doc_id,
            title=m.title,
            category=m.category,
            tags=tags,
            content=m.content,
            is_active=m.is_active,
        )

    def list_kb_documents(self, active_only: bool = True) -> List[KnowledgeDocument]:
        q = self.db.query(KnowledgeDocumentModel)
        if active_only:
            q = q.filter(KnowledgeDocumentModel.is_active == True)
        results = []
        for m in q.all():
            tags = json.loads(m.tags_json) if m.tags_json else []
            results.append(KnowledgeDocument(
                doc_id=m.doc_id,
                title=m.title,
                category=m.category,
                tags=tags,
                content=m.content,
                is_active=m.is_active,
            ))
        return results

    # Ticket
    def create_ticket(self, ticket: Ticket) -> Ticket:
        m = TicketModel(
            id=ticket.id,
            customer_id=ticket.customer_id,
            order_id=ticket.order_id,
            subject=ticket.subject,
            description=ticket.description,
            created_at=ticket.created_at,
            category=ticket.category.value if ticket.category else None,
            priority=ticket.priority.value if ticket.priority else None,
            status=ticket.status.value,
            escalate=ticket.escalate,
            escalation_reason=ticket.escalation_reason,
        )
        self.db.add(m)
        self.db.commit()
        return ticket

    def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        m = self.db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
        if not m:
            return None
        return Ticket(
            id=m.id,
            customer_id=m.customer_id,
            order_id=m.order_id,
            subject=m.subject,
            description=m.description,
            created_at=m.created_at,
            category=CategoryEnum(m.category) if m.category else None,
            priority=PriorityEnum(m.priority) if m.priority else None,
            status=TicketStatusEnum(m.status),
            escalate=m.escalate,
            escalation_reason=m.escalation_reason,
        )

    def list_tickets(self, status: Optional[str] = None) -> List[Ticket]:
        q = self.db.query(TicketModel)
        if status:
            q = q.filter(TicketModel.status == status)
        results = []
        for m in q.order_by(TicketModel.created_at.desc()).all():
            results.append(Ticket(
                id=m.id,
                customer_id=m.customer_id,
                order_id=m.order_id,
                subject=m.subject,
                description=m.description,
                created_at=m.created_at,
                category=CategoryEnum(m.category) if m.category else None,
                priority=PriorityEnum(m.priority) if m.priority else None,
                status=TicketStatusEnum(m.status),
                escalate=m.escalate,
                escalation_reason=m.escalation_reason,
            ))
        return results

    def update_ticket(self, ticket_id: str, **kwargs) -> Optional[Ticket]:
        m = self.db.query(TicketModel).filter(TicketModel.id == ticket_id).first()
        if not m:
            return None
        for k, v in kwargs.items():
            if hasattr(m, k):
                if isinstance(v, Enum):
                    setattr(m, k, v.value)
                else:
                    setattr(m, k, v)
        self.db.commit()
        return self.get_ticket(ticket_id)

    # Draft
    def save_draft(self, draft: DraftResponse) -> DraftResponse:
        m = DraftModel(
            ticket_id=draft.ticket_id,
            response_text=draft.response_text,
            cited_doc_ids_json=json.dumps(draft.cited_doc_ids),
            confidence_score=draft.confidence_score,
            is_grounded=draft.is_grounded,
            needs_escalation=draft.needs_escalation,
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        self.db.add(m)
        self.db.commit()
        return draft

    def get_latest_draft(self, ticket_id: str) -> Optional[DraftResponse]:
        m = (
            self.db.query(DraftModel)
            .filter(DraftModel.ticket_id == ticket_id)
            .order_by(DraftModel.id.desc())
            .first()
        )
        if not m:
            return None
        cited_doc_ids = json.loads(m.cited_doc_ids_json) if m.cited_doc_ids_json else []
        return DraftResponse(
            ticket_id=m.ticket_id,
            response_text=m.response_text,
            cited_doc_ids=cited_doc_ids,
            confidence_score=m.confidence_score,
            is_grounded=m.is_grounded,
            needs_escalation=m.needs_escalation,
        )

    # Operational Actions & Idempotency
    def get_action_by_idempotency_key(self, idempotency_key: str) -> Optional[OperationalAction]:
        m = self.db.query(OperationalActionModel).filter(OperationalActionModel.idempotency_key == idempotency_key).first()
        if not m:
            return None
        return OperationalAction(
            id=m.id,
            ticket_id=m.ticket_id,
            action_type=ActionTypeEnum(m.action_type),
            parameters=json.loads(m.parameters_json) if m.parameters_json else {},
            idempotency_key=m.idempotency_key,
            justification=m.justification,
            status=ActionStatusEnum(m.status),
            created_at=m.created_at,
            executed_at=m.executed_at,
        )

    def create_operational_action(self, action: OperationalAction) -> OperationalAction:
        existing = self.get_action_by_idempotency_key(action.idempotency_key)
        if existing:
            return existing
        m = OperationalActionModel(
            id=action.id,
            ticket_id=action.ticket_id,
            action_type=action.action_type.value,
            parameters_json=json.dumps(action.parameters),
            idempotency_key=action.idempotency_key,
            justification=action.justification,
            status=action.status.value,
            created_at=action.created_at,
            executed_at=action.executed_at,
        )
        self.db.add(m)
        self.db.commit()
        return action

    def get_operational_action(self, action_id: str) -> Optional[OperationalAction]:
        m = self.db.query(OperationalActionModel).filter(OperationalActionModel.id == action_id).first()
        if not m:
            return None
        return OperationalAction(
            id=m.id,
            ticket_id=m.ticket_id,
            action_type=ActionTypeEnum(m.action_type),
            parameters=json.loads(m.parameters_json) if m.parameters_json else {},
            idempotency_key=m.idempotency_key,
            justification=m.justification,
            status=ActionStatusEnum(m.status),
            created_at=m.created_at,
            executed_at=m.executed_at,
        )

    def list_actions(self, status: Optional[str] = None, ticket_id: Optional[str] = None) -> List[OperationalAction]:
        q = self.db.query(OperationalActionModel)
        if status:
            q = q.filter(OperationalActionModel.status == status)
        if ticket_id:
            q = q.filter(OperationalActionModel.ticket_id == ticket_id)
        results = []
        for m in q.order_by(OperationalActionModel.created_at.desc()).all():
            results.append(OperationalAction(
                id=m.id,
                ticket_id=m.ticket_id,
                action_type=ActionTypeEnum(m.action_type),
                parameters=json.loads(m.parameters_json) if m.parameters_json else {},
                idempotency_key=m.idempotency_key,
                justification=m.justification,
                status=ActionStatusEnum(m.status),
                created_at=m.created_at,
                executed_at=m.executed_at,
            ))
        return results

    def update_action_status(self, action_id: str, status: ActionStatusEnum, executed_at: Optional[str] = None) -> Optional[OperationalAction]:
        m = self.db.query(OperationalActionModel).filter(OperationalActionModel.id == action_id).first()
        if not m:
            return None
        m.status = status.value
        if executed_at:
            m.executed_at = executed_at
        self.db.commit()
        return self.get_operational_action(action_id)

    # Audit Trace
    def add_audit_trace(self, trace: AuditTrace) -> AuditTrace:
        m = AuditTraceModel(
            trace_id=trace.trace_id,
            ticket_id=trace.ticket_id,
            step_name=trace.step_name,
            input_json=json.dumps(trace.input_data) if trace.input_data else None,
            docs_json=json.dumps(trace.retrieved_docs) if trace.retrieved_docs else None,
            flags_json=json.dumps(trace.guardrail_flags) if trace.guardrail_flags else None,
            output_json=json.dumps(trace.output_data) if trace.output_data else None,
            created_at=trace.created_at,
        )
        self.db.add(m)
        self.db.commit()
        return trace

    def list_audit_traces(self, ticket_id: Optional[str] = None) -> List[AuditTrace]:
        q = self.db.query(AuditTraceModel)
        if ticket_id:
            q = q.filter(AuditTraceModel.ticket_id == ticket_id)
        results = []
        for m in q.order_by(AuditTraceModel.id.asc()).all():
            results.append(AuditTrace(
                id=m.id,
                trace_id=m.trace_id,
                ticket_id=m.ticket_id,
                step_name=m.step_name,
                input_data=json.loads(m.input_json) if m.input_json else None,
                retrieved_docs=json.loads(m.docs_json) if m.docs_json else None,
                guardrail_flags=json.loads(m.flags_json) if m.flags_json else None,
                output_data=json.loads(m.output_json) if m.output_json else None,
                created_at=m.created_at,
            ))
        return results
