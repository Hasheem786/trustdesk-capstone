import pytest
from src.trustdesk.models.domain import (
    Ticket,
    Order,
    CategoryEnum,
    PriorityEnum,
)
from src.trustdesk.ai.mock_adapter import MockAIAdapter

@pytest.mark.asyncio
async def test_triage_refund_within_window(mock_ai):
    order = Order(
        id="ORD-TEST-1",
        customer_id="CUST-1",
        total_amount=100.0,
        status="delivered",
        order_date="2026-09-15T00:00:00Z",
        delivered_date="2026-09-20T00:00:00Z",
    )
    ticket = Ticket(
        id="TCK-1",
        customer_id="CUST-1",
        order_id="ORD-TEST-1",
        subject="Return item",
        description="I want to return my item, delivered 10 days ago.",
        created_at="2026-09-30T00:00:00Z",
    )
    result = await mock_ai.triage_ticket(ticket, order=order)
    assert result.category == CategoryEnum.REFUND
    assert result.priority == PriorityEnum.MEDIUM
    assert result.escalate is False

@pytest.mark.asyncio
async def test_triage_refund_exceeding_30_days_escalates(mock_ai):
    order = Order(
        id="ORD-TEST-2",
        customer_id="CUST-2",
        total_amount=200.0,
        status="delivered",
        order_date="2026-06-01T00:00:00Z",
        delivered_date="2026-06-05T00:00:00Z",
    )
    ticket = Ticket(
        id="TCK-2",
        customer_id="CUST-2",
        order_id="ORD-TEST-2",
        subject="Return item from June",
        description="I want to return this product I bought months ago.",
        created_at="2026-09-30T00:00:00Z",
    )
    result = await mock_ai.triage_ticket(ticket, order=order)
    assert result.category == CategoryEnum.REFUND
    assert result.escalate is True
    assert "exceeds 30-day window" in result.escalation_reason

@pytest.mark.asyncio
async def test_triage_warranty_hardware_defect(mock_ai):
    order = Order(
        id="ORD-TEST-3",
        customer_id="CUST-3",
        total_amount=350.0,
        status="delivered",
        order_date="2026-05-01T00:00:00Z",
        delivered_date="2026-05-05T00:00:00Z",
    )
    ticket = Ticket(
        id="TCK-3",
        customer_id="CUST-3",
        order_id="ORD-TEST-3",
        subject="Monitor defective",
        description="The display screen is broken and flickering internally.",
        created_at="2026-09-30T00:00:00Z",
    )
    result = await mock_ai.triage_ticket(ticket, order=order)
    assert result.category == CategoryEnum.WARRANTY
    assert result.priority == PriorityEnum.HIGH
    assert result.escalate is False
