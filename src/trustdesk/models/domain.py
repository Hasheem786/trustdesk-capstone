from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class CategoryEnum(str, Enum):
    SHIPPING = "shipping"
    REFUND = "refund"
    WARRANTY = "warranty"
    BILLING = "billing"
    ACCOUNT_SECURITY = "account_security"
    GENERAL = "general"

class PriorityEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class TicketStatusEnum(str, Enum):
    NEW = "new"
    TRIAGED = "triaged"
    PENDING_APPROVAL = "pending_approval"
    RESOLVED = "resolved"
    ESCALATED = "escalated"

class ActionTypeEnum(str, Enum):
    START_REFUND_REVIEW = "start_refund_review"
    CREATE_REPLACEMENT_ORDER = "create_replacement_order"

class ActionStatusEnum(str, Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"

class Customer(BaseModel):
    id: str
    name: str
    email: str
    tier: str = "standard"  # "standard" | "vip"
    created_at: str

class OrderItem(BaseModel):
    item_id: str
    name: str
    price: float
    warranty_days: int = 365

class Order(BaseModel):
    id: str
    customer_id: str
    items: List[OrderItem] = []
    total_amount: float
    status: str  # "delivered", "in_transit", "cancelled"
    order_date: str
    delivered_date: Optional[str] = None
    tracking_number: Optional[str] = None

class KnowledgeDocument(BaseModel):
    doc_id: str
    title: str
    category: str
    tags: List[str] = []
    content: str
    is_active: bool = True

class TicketCreate(BaseModel):
    customer_id: str
    order_id: Optional[str] = None
    subject: str
    description: str
    created_at: Optional[str] = None

class Ticket(BaseModel):
    id: str
    customer_id: str
    order_id: Optional[str] = None
    subject: str
    description: str
    created_at: str
    category: Optional[CategoryEnum] = None
    priority: Optional[PriorityEnum] = None
    status: TicketStatusEnum = TicketStatusEnum.NEW
    escalate: bool = False
    escalation_reason: Optional[str] = None

class TriageResult(BaseModel):
    category: CategoryEnum
    priority: PriorityEnum
    escalate: bool
    escalation_reason: Optional[str] = None
    confidence_score: float = 1.0

class GuardrailResult(BaseModel):
    is_safe: bool = True
    flag_type: Optional[str] = None  # "PROMPT_INJECTION", "COUPON_EXPLOIT", "SECRET_LEAK", "POISONED_DOC", "PRIVILEGE_BYPASS"
    reason: Optional[str] = None
    sanitized_content: Optional[str] = None

class DraftResponse(BaseModel):
    ticket_id: str
    response_text: str
    cited_doc_ids: List[str] = []
    confidence_score: float = 1.0
    is_grounded: bool = True
    needs_escalation: bool = False

class OperationalAction(BaseModel):
    id: str
    ticket_id: str
    action_type: ActionTypeEnum
    parameters: Dict[str, Any] = {}
    idempotency_key: str
    justification: str
    status: ActionStatusEnum = ActionStatusEnum.PENDING_APPROVAL
    created_at: str
    executed_at: Optional[str] = None

class AuditTrace(BaseModel):
    id: Optional[int] = None
    trace_id: str
    ticket_id: str
    step_name: str
    input_data: Optional[Dict[str, Any]] = None
    retrieved_docs: Optional[List[str]] = None
    guardrail_flags: Optional[List[str]] = None
    output_data: Optional[Dict[str, Any]] = None
    created_at: str

class EvalCase(BaseModel):
    id: str
    ticket_id: str
    customer_id: str
    order_id: Optional[str] = None
    created_at: str
    subject: str
    description: str
    expected_category: CategoryEnum
    expected_priority: PriorityEnum
    expected_escalate: bool
    expected_citations: List[str] = []
    expected_action: Optional[str] = None
    is_adversarial: bool = False
