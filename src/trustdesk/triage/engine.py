import uuid
from datetime import datetime
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from src.trustdesk.models.domain import (
    Ticket,
    TriageResult,
    GuardrailResult,
    AuditTrace,
    TicketStatusEnum,
)
from src.trustdesk.storage.repository import Repository
from src.trustdesk.guardrails.input_guard import InputGuardrail
from src.trustdesk.ai.base import AIProvider

class TriageEngine:
    """Intelligent Ticket Triage Engine with Guardrail Filtering and Context Resolution."""

    def __init__(self, ai_provider: AIProvider, repo: Repository):
        self.ai_provider = ai_provider
        self.repo = repo
        self.input_guard = InputGuardrail()

    async def triage(self, ticket: Ticket, trace_id: Optional[str] = None) -> Tuple[TriageResult, GuardrailResult]:
        if not trace_id:
            trace_id = f"TRC-{uuid.uuid4().hex[:8].upper()}"

        full_text = f"{ticket.subject}\n{ticket.description}"

        # 1. Input Guardrail
        guard_res = self.input_guard.validate(full_text)

        # 2. Fetch Customer and Order Context
        customer = self.repo.get_customer(ticket.customer_id) if ticket.customer_id else None
        order = self.repo.get_order(ticket.order_id) if ticket.order_id else None

        # 3. AI Triage Classification
        triage_res = await self.ai_provider.triage_ticket(ticket, order, customer)

        # If guardrail flagged an attack, enforce escalation
        if not guard_res.is_safe:
            triage_res.escalate = True
            triage_res.escalation_reason = f"Security Guardrail Alert: {guard_res.reason}"

        # 4. Update Ticket Record
        new_status = TicketStatusEnum.ESCALATED if triage_res.escalate else TicketStatusEnum.TRIAGED
        self.repo.update_ticket(
            ticket.id,
            category=triage_res.category,
            priority=triage_res.priority,
            status=new_status,
            escalate=triage_res.escalate,
            escalation_reason=triage_res.escalation_reason,
        )

        # 5. Record Audit Trace
        self.repo.add_audit_trace(AuditTrace(
            trace_id=trace_id,
            ticket_id=ticket.id,
            step_name="triage",
            input_data={"subject": ticket.subject, "description": ticket.description},
            guardrail_flags=[guard_res.flag_type] if not guard_res.is_safe else [],
            output_data={
                "category": triage_res.category.value,
                "priority": triage_res.priority.value,
                "escalate": triage_res.escalate,
                "escalation_reason": triage_res.escalation_reason,
            },
            created_at=datetime.utcnow().isoformat() + "Z",
        ))

        return triage_res, guard_res
