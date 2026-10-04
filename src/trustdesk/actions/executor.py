import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

from src.trustdesk.models.domain import (
    Ticket,
    TriageResult,
    OperationalAction,
    ActionTypeEnum,
    ActionStatusEnum,
    TicketStatusEnum,
    AuditTrace,
)
from src.trustdesk.storage.repository import Repository
from src.trustdesk.ai.base import AIProvider

class ActionExecutor:
    """Approval-gated operational tool executor guarded by deterministic idempotency keys."""

    def __init__(self, ai_provider: AIProvider, repo: Repository):
        self.ai_provider = ai_provider
        self.repo = repo

    async def propose_operational_action(
        self,
        ticket: Ticket,
        triage: TriageResult,
        trace_id: Optional[str] = None,
    ) -> Optional[OperationalAction]:
        if not trace_id:
            trace_id = f"TRC-{uuid.uuid4().hex[:8].upper()}"

        order = self.repo.get_order(ticket.order_id) if ticket.order_id else None

        # 1. Propose action via AI adapter
        action = await self.ai_provider.propose_action(ticket, order, triage)
        if not action:
            return None

        # 2. Idempotency Check: check if already exists
        existing = self.repo.get_action_by_idempotency_key(action.idempotency_key)
        if existing:
            return existing

        # 3. Save pending action
        created_action = self.repo.create_operational_action(action)

        # 4. Mark ticket as pending_approval
        self.repo.update_ticket(ticket.id, status=TicketStatusEnum.PENDING_APPROVAL)

        # 5. Record trace
        self.repo.add_audit_trace(AuditTrace(
            trace_id=trace_id,
            ticket_id=ticket.id,
            step_name="propose_action",
            input_data={"triage_category": triage.category.value},
            output_data={
                "action_id": created_action.id,
                "action_type": created_action.action_type.value,
                "idempotency_key": created_action.idempotency_key,
                "status": created_action.status.value,
            },
            created_at=datetime.utcnow().isoformat() + "Z",
        ))

        return created_action

    def approve_action(
        self,
        action_id: str,
        reviewer_id: str = "agent_human",
    ) -> Tuple[bool, str, Optional[OperationalAction]]:
        """Executes a previously blocked operational action upon human approval."""
        action = self.repo.get_operational_action(action_id)
        if not action:
            return False, f"Action with ID '{action_id}' not found.", None

        if action.status != ActionStatusEnum.PENDING_APPROVAL:
            return False, f"Action is already '{action.status.value}' and cannot be approved again.", action

        now = datetime.utcnow().isoformat() + "Z"

        # Execute business logic
        if action.action_type == ActionTypeEnum.START_REFUND_REVIEW:
            # Operational execution: log refund review initiated
            execution_msg = f"Refund review initiated for order {action.parameters.get('order_id')} ($ {action.parameters.get('amount')})."
        elif action.action_type == ActionTypeEnum.CREATE_REPLACEMENT_ORDER:
            # Operational execution: create replacement order
            execution_msg = f"Replacement order created for item {action.parameters.get('item_id')}."
        else:
            execution_msg = f"Action {action.action_type.value} executed."

        # Update action to EXECUTED
        updated = self.repo.update_action_status(
            action_id=action_id,
            status=ActionStatusEnum.EXECUTED,
            executed_at=now,
        )

        # Update ticket status to RESOLVED
        self.repo.update_ticket(action.ticket_id, status=TicketStatusEnum.RESOLVED)

        # Audit trace
        self.repo.add_audit_trace(AuditTrace(
            trace_id=f"TRC-{uuid.uuid4().hex[:8].upper()}",
            ticket_id=action.ticket_id,
            step_name="execute_action",
            input_data={"action_id": action_id, "reviewer": reviewer_id},
            output_data={"status": "EXECUTED", "message": execution_msg, "executed_at": now},
            created_at=now,
        ))

        return True, execution_msg, updated

    def reject_action(
        self,
        action_id: str,
        reason: str = "Rejected by support operator",
        reviewer_id: str = "agent_human",
    ) -> Tuple[bool, str, Optional[OperationalAction]]:
        """Rejects a proposed action."""
        action = self.repo.get_operational_action(action_id)
        if not action:
            return False, f"Action with ID '{action_id}' not found.", None

        if action.status != ActionStatusEnum.PENDING_APPROVAL:
            return False, f"Action is already '{action.status.value}'.", action

        now = datetime.utcnow().isoformat() + "Z"
        updated = self.repo.update_action_status(
            action_id=action_id,
            status=ActionStatusEnum.REJECTED,
            executed_at=now,
        )

        self.repo.update_ticket(action.ticket_id, status=TicketStatusEnum.TRIAGED)

        self.repo.add_audit_trace(AuditTrace(
            trace_id=f"TRC-{uuid.uuid4().hex[:8].upper()}",
            ticket_id=action.ticket_id,
            step_name="reject_action",
            input_data={"action_id": action_id, "reason": reason, "reviewer": reviewer_id},
            output_data={"status": "REJECTED"},
            created_at=now,
        ))

        return True, "Action successfully rejected.", updated
