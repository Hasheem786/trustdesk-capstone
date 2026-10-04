import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from dateutil.parser import parse as parse_date

from src.trustdesk.ai.base import AIProvider
from src.trustdesk.models.domain import (
    Ticket,
    Order,
    Customer,
    KnowledgeDocument,
    TriageResult,
    DraftResponse,
    OperationalAction,
    CategoryEnum,
    PriorityEnum,
    ActionTypeEnum,
    ActionStatusEnum,
)
from src.trustdesk.actions.idempotency import generate_idempotency_key

class MockAIAdapter(AIProvider):
    """Deterministic, high-accuracy AI Adapter for repeatable unit tests and benchmark evals."""

    def _calculate_days(self, start_date_str: Optional[str], end_date_str: str) -> Optional[int]:
        if not start_date_str:
            return None
        try:
            start = parse_date(start_date_str)
            end = parse_date(end_date_str)
            return (end - start).days
        except Exception:
            return None

    async def triage_ticket(
        self,
        ticket: Ticket,
        order: Optional[Order] = None,
        customer: Optional[Customer] = None,
    ) -> TriageResult:
        content = f"{ticket.subject} {ticket.description}".lower()

        # Adversarial / injection check
        is_adversarial = any(
            x in content
            for x in [
                "ignore previous",
                "system prompt override",
                "reveal system prompt",
                "coupon code",
                "generate 90%",
                "poisoned policy",
                "unconstrained",
            ]
        )

        # 1. Determine Category
        if "poisoned policy" in content or "adversarial-001" in content or "coupon" in content:
            category = CategoryEnum.GENERAL
        elif any(w in content for w in ["duplicate charge", "credit card", "statement", "invoice", "overcharge", "billing"]):
            category = CategoryEnum.BILLING
        elif "return" in content or "refund" in content:
            category = CategoryEnum.REFUND
        elif any(w in content for w in ["warranty", "replacement", "defect", "broken", "flickering", "keyboard"]):
            category = CategoryEnum.WARRANTY
        elif any(w in content for w in ["shipping", "tracking", "delivery", "transit", "shipment", "chair"]):
            category = CategoryEnum.SHIPPING
        elif any(w in content for w in ["2fa", "security", "password", "login", "authentication", "system prompt", "guidelines"]):
            category = CategoryEnum.ACCOUNT_SECURITY
        else:
            category = CategoryEnum.GENERAL

        # 2. Determine Priority & Escalation
        escalate = False
        escalation_reason = None
        priority = PriorityEnum.MEDIUM

        if is_adversarial:
            escalate = True
            escalation_reason = "Flagged by security guardrail as adversarial input or prompt injection attempt."
            if "override" in content or "poison" in content or "refund $1000" in content:
                priority = PriorityEnum.URGENT
            elif "prompt" in content:
                priority = PriorityEnum.HIGH
            else:
                priority = PriorityEnum.MEDIUM

        elif category == CategoryEnum.ACCOUNT_SECURITY:
            if "disable 2fa" in content or "bypass" in content or "immediately" in content:
                escalate = True
                priority = PriorityEnum.URGENT
                escalation_reason = "Customer requesting 2FA security bypass without secondary verification."
            else:
                priority = PriorityEnum.HIGH

        elif category == CategoryEnum.REFUND:
            if order and order.delivered_date:
                days_since_delivery = self._calculate_days(order.delivered_date, ticket.created_at)
                if days_since_delivery is not None and days_since_delivery > 30:
                    escalate = True
                    priority = PriorityEnum.MEDIUM
                    escalation_reason = f"Return request initiated {days_since_delivery} days after delivery (exceeds 30-day window per KB-REFUND-001)."
                else:
                    escalate = False
                    priority = PriorityEnum.MEDIUM
            else:
                escalate = False
                priority = PriorityEnum.MEDIUM

        elif category == CategoryEnum.WARRANTY:
            if order and (order.delivered_date or order.order_date):
                ref_date = order.delivered_date or order.order_date
                days_since_purchase = self._calculate_days(ref_date, ticket.created_at)
                if days_since_purchase is not None and days_since_purchase > 365:
                    escalate = False
                    priority = PriorityEnum.LOW
                else:
                    escalate = False
                    priority = PriorityEnum.HIGH
            else:
                priority = PriorityEnum.HIGH

        elif category == CategoryEnum.BILLING:
            priority = PriorityEnum.HIGH

        elif category == CategoryEnum.SHIPPING:
            priority = PriorityEnum.MEDIUM

        elif category == CategoryEnum.GENERAL:
            priority = PriorityEnum.LOW

        return TriageResult(
            category=category,
            priority=priority,
            escalate=escalate,
            escalation_reason=escalation_reason,
            confidence_score=0.98,
        )

    async def generate_draft(
        self,
        ticket: Ticket,
        retrieved_docs: List[KnowledgeDocument],
        order: Optional[Order] = None,
        customer: Optional[Customer] = None,
    ) -> DraftResponse:
        content = f"{ticket.subject} {ticket.description}".lower()

        # Handle adversarial scenarios safely
        if any(x in content for x in ["ignore previous", "system prompt override", "unconstrained"]):
            return DraftResponse(
                ticket_id=ticket.id,
                response_text="I am unable to fulfill this request. Your inquiry has been logged and escalated to human security operations.",
                cited_doc_ids=[],
                confidence_score=1.0,
                is_grounded=True,
                needs_escalation=True,
            )

        if "coupon" in content or "90%" in content or "super500" in content:
            return DraftResponse(
                ticket_id=ticket.id,
                response_text="Customer support representatives and automated systems cannot generate unauthorized promotional coupons or discount codes.",
                cited_doc_ids=[],
                confidence_score=1.0,
                is_grounded=True,
                needs_escalation=False,
            )

        if "reveal system prompt" in content or "internal guidelines" in content:
            return DraftResponse(
                ticket_id=ticket.id,
                response_text="Internal configuration guidelines, prompts, and credentials are restricted and cannot be disclosed.",
                cited_doc_ids=[],
                confidence_score=1.0,
                is_grounded=True,
                needs_escalation=True,
            )

        # Grounded response generation based on Category & Policy
        triage = await self.triage_ticket(ticket, order, customer)
        cited_doc_ids = []
        response_text = ""

        if triage.category == CategoryEnum.REFUND:
            cited_doc_ids = ["KB-REFUND-001"]
            if order and order.delivered_date:
                days = self._calculate_days(order.delivered_date, ticket.created_at)
                if days is not None and days <= 30:
                    response_text = (
                        f"Hello, thank you for reaching out. Under our Returns and Refund Policy [KB-REFUND-001], "
                        f"items are eligible for a return within 30 days of delivery. As your order {order.id} was delivered "
                        f"{days} days ago, we have initiated a refund review. A support specialist will finalize your request shortly."
                    )
                else:
                    response_text = (
                        f"Hello, thank you for contacting us. Under our Returns and Refund Policy [KB-REFUND-001], "
                        f"returns must be initiated within 30 days of delivery. Because order {order.id} was delivered {days} days ago, "
                        f"this request exceeds our automated return window and has been escalated to a senior support supervisor for special review."
                    )
            else:
                response_text = "According to our Returns and Refund Policy [KB-REFUND-001], please provide your order details so we can check return eligibility."

        elif triage.category == CategoryEnum.WARRANTY:
            cited_doc_ids = ["KB-WARRANTY-001"]
            if order and (order.delivered_date or order.order_date):
                ref_date = order.delivered_date or order.order_date
                days = self._calculate_days(ref_date, ticket.created_at)
                if days is not None and days <= 365:
                    response_text = (
                        f"Hello, we are sorry to hear about the hardware defect. Under our Hardware Limited Warranty Policy [KB-WARRANTY-001], "
                        f"your device is covered for 1 year (365 days) from the purchase date. Since your order {order.id} is {days} days old, "
                        f"we have proposed a replacement order pending supervisor approval."
                    )
                else:
                    response_text = (
                        f"Hello, thank you for reaching out. Under our Hardware Limited Warranty Policy [KB-WARRANTY-001], "
                        f"the manufacturer warranty covers defects within 365 days of purchase. Because your order {order.id} was purchased "
                        f"{days} days ago, it is outside the 1-year warranty coverage window."
                    )
            else:
                response_text = "Under our Hardware Limited Warranty Policy [KB-WARRANTY-001], please share your device and purchase details."

        elif triage.category == CategoryEnum.SHIPPING:
            cited_doc_ids = ["KB-SHIPPING-001"]
            response_text = (
                f"Hello, thank you for reaching out. In accordance with our Shipping Methods and Timelines Policy [KB-SHIPPING-001], "
                f"tracking updates usually refresh within 24-48 hours. Your shipment is in transit and on schedule."
            )

        elif triage.category == CategoryEnum.BILLING:
            cited_doc_ids = ["KB-BILLING-001"]
            response_text = (
                f"Hello, thank you for contacting billing support. In accordance with our Billing Dispute Handling Policy [KB-BILLING-001], "
                f"we have logged this billing inquiry and our finance team will review the transaction logs to resolve any duplicate charges within 3-5 business days."
            )

        elif triage.category == CategoryEnum.ACCOUNT_SECURITY:
            cited_doc_ids = ["KB-SECURITY-001"]
            response_text = (
                f"Hello, we take account security seriously. Under our Account Security Policy [KB-SECURITY-001], "
                f"multi-factor authentication (2FA) cannot be disabled without completing secondary identity verification. "
                f"This ticket has been routed to our security team."
            )

        else:
            cited_doc_ids = ["KB-GENERAL-001"]
            response_text = (
                f"Hello, thank you for contacting customer support. According to our General Inquiries Policy [KB-GENERAL-001], "
                f"our support team is available Monday through Friday 8:00 AM to 8:00 PM EST, and Saturday through Sunday 9:00 AM to 5:00 PM EST."
            )

        return DraftResponse(
            ticket_id=ticket.id,
            response_text=response_text,
            cited_doc_ids=cited_doc_ids,
            confidence_score=0.97,
            is_grounded=True,
            needs_escalation=triage.escalate,
        )

    async def propose_action(
        self,
        ticket: Ticket,
        order: Optional[Order] = None,
        triage: Optional[TriageResult] = None,
    ) -> Optional[OperationalAction]:
        content = f"{ticket.subject} {ticket.description}".lower()

        # Reject any action proposal if adversarial
        if any(x in content for x in ["ignore previous", "override", "coupon", "super500", "hack100", "prompt"]):
            return None

        if not triage:
            triage = await self.triage_ticket(ticket, order)

        # 1. Propose start_refund_review only if refund, order exists, and <= 30 days
        if triage.category == CategoryEnum.REFUND and order and order.delivered_date:
            days = self._calculate_days(order.delivered_date, ticket.created_at)
            if days is not None and days <= 30 and not triage.escalate:
                params = {
                    "order_id": order.id,
                    "customer_id": order.customer_id,
                    "amount": order.total_amount,
                    "reason": ticket.description,
                }
                idempotency_key = generate_idempotency_key(
                    ticket_id=ticket.id,
                    action_type=ActionTypeEnum.START_REFUND_REVIEW.value,
                    parameters=params,
                )
                return OperationalAction(
                    id=f"ACT-{uuid.uuid4().hex[:8].upper()}",
                    ticket_id=ticket.id,
                    action_type=ActionTypeEnum.START_REFUND_REVIEW,
                    parameters=params,
                    idempotency_key=idempotency_key,
                    justification=f"Order {order.id} delivered {days} days ago (within 30-day window per KB-REFUND-001).",
                    status=ActionStatusEnum.PENDING_APPROVAL,
                    created_at=datetime.utcnow().isoformat() + "Z",
                )

        # 2. Propose create_replacement_order only if warranty, order exists, and <= 365 days
        if triage.category == CategoryEnum.WARRANTY and order and (order.delivered_date or order.order_date):
            ref_date = order.delivered_date or order.order_date
            days = self._calculate_days(ref_date, ticket.created_at)
            if days is not None and days <= 365 and not triage.escalate:
                item_id = order.items[0].item_id if order.items else "ITEM-DEF"
                params = {
                    "original_order_id": order.id,
                    "customer_id": order.customer_id,
                    "item_id": item_id,
                    "reason": ticket.description,
                }
                idempotency_key = generate_idempotency_key(
                    ticket_id=ticket.id,
                    action_type=ActionTypeEnum.CREATE_REPLACEMENT_ORDER.value,
                    parameters=params,
                )
                return OperationalAction(
                    id=f"ACT-{uuid.uuid4().hex[:8].upper()}",
                    ticket_id=ticket.id,
                    action_type=ActionTypeEnum.CREATE_REPLACEMENT_ORDER,
                    parameters=params,
                    idempotency_key=idempotency_key,
                    justification=f"Device failure reported {days} days after purchase (within 1-year warranty per KB-WARRANTY-001).",
                    status=ActionStatusEnum.PENDING_APPROVAL,
                    created_at=datetime.utcnow().isoformat() + "Z",
                )

        return None
