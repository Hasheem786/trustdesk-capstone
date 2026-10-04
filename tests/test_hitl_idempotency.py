import pytest
from src.trustdesk.actions.idempotency import generate_idempotency_key
from src.trustdesk.actions.executor import ActionExecutor
from src.trustdesk.models.domain import (
    Ticket,
    Order,
    TriageResult,
    CategoryEnum,
    PriorityEnum,
    ActionTypeEnum,
    ActionStatusEnum,
)

def test_idempotency_key_deterministic():
    key1 = generate_idempotency_key("TCK-1", "start_refund_review", {"amount": 100, "order": "ORD-1"})
    key2 = generate_idempotency_key("TCK-1", "start_refund_review", {"order": "ORD-1", "amount": 100})
    assert key1 == key2
    assert len(key1) == 64

@pytest.mark.asyncio
async def test_hitl_action_blocked_until_approval(mock_ai, repo):
    executor = ActionExecutor(mock_ai, repo)

    ticket = Ticket(
        id="TCK-ACT-1",
        customer_id="CUST-001",
        order_id="ORD-1001",
        subject="Refund request within 14 days",
        description="I want to return headphones.",
        created_at="2026-10-04T10:00:00Z",
    )
    repo.create_ticket(ticket)

    triage = TriageResult(
        category=CategoryEnum.REFUND,
        priority=PriorityEnum.MEDIUM,
        escalate=False,
    )

    # 1. Propose action
    action = await executor.propose_operational_action(ticket, triage)
    assert action is not None
    assert action.action_type == ActionTypeEnum.START_REFUND_REVIEW
    assert action.status == ActionStatusEnum.PENDING_APPROVAL
    assert action.executed_at is None

    # 2. Test Idempotency: re-propose same action
    re_action = await executor.propose_operational_action(ticket, triage)
    assert re_action.idempotency_key == action.idempotency_key
    assert re_action.id == action.id

    # 3. Human Approval & Execution
    success, msg, executed_action = executor.approve_action(action.id)
    assert success is True
    assert executed_action.status == ActionStatusEnum.EXECUTED
    assert executed_action.executed_at is not None

    # 4. Attempt to execute again should be rejected
    second_try, err_msg, _ = executor.approve_action(action.id)
    assert second_try is False
    assert "already" in err_msg.lower()
