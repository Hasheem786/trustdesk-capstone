from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class CustomerModel(Base):
    __tablename__ = "customers"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    tier = Column(String(20), default="standard")
    created_at = Column(String(50), nullable=False)

class OrderModel(Base):
    __tablename__ = "orders"

    id = Column(String(50), primary_key=True)
    customer_id = Column(String(50), ForeignKey("customers.id"), nullable=False)
    items_json = Column(Text, default="[]")
    total_amount = Column(Float, default=0.0)
    status = Column(String(50), default="delivered")
    order_date = Column(String(50), nullable=False)
    delivered_date = Column(String(50), nullable=True)
    tracking_number = Column(String(100), nullable=True)

class KnowledgeDocumentModel(Base):
    __tablename__ = "kb_documents"

    doc_id = Column(String(50), primary_key=True)
    title = Column(String(200), nullable=False)
    category = Column(String(50), nullable=False)
    tags_json = Column(Text, default="[]")
    content = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)

class TicketModel(Base):
    __tablename__ = "tickets"

    id = Column(String(50), primary_key=True)
    customer_id = Column(String(50), nullable=False)
    order_id = Column(String(50), nullable=True)
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(String(50), nullable=False)
    category = Column(String(50), nullable=True)
    priority = Column(String(50), nullable=True)
    status = Column(String(50), default="new")
    escalate = Column(Boolean, default=False)
    escalation_reason = Column(Text, nullable=True)

class DraftModel(Base):
    __tablename__ = "drafts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(String(50), ForeignKey("tickets.id"), nullable=False)
    response_text = Column(Text, nullable=False)
    cited_doc_ids_json = Column(Text, default="[]")
    confidence_score = Column(Float, default=1.0)
    is_grounded = Column(Boolean, default=True)
    needs_escalation = Column(Boolean, default=False)
    created_at = Column(String(50), nullable=False)

class OperationalActionModel(Base):
    __tablename__ = "operational_actions"

    id = Column(String(50), primary_key=True)
    ticket_id = Column(String(50), ForeignKey("tickets.id"), nullable=False)
    action_type = Column(String(50), nullable=False)
    parameters_json = Column(Text, default="{}")
    idempotency_key = Column(String(64), unique=True, nullable=False, index=True)
    justification = Column(Text, nullable=False)
    status = Column(String(50), default="PENDING_APPROVAL")
    created_at = Column(String(50), nullable=False)
    executed_at = Column(String(50), nullable=True)

class AuditTraceModel(Base):
    __tablename__ = "audit_traces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trace_id = Column(String(50), nullable=False, index=True)
    ticket_id = Column(String(50), nullable=False, index=True)
    step_name = Column(String(50), nullable=False)
    input_json = Column(Text, nullable=True)
    docs_json = Column(Text, nullable=True)
    flags_json = Column(Text, nullable=True)
    output_json = Column(Text, nullable=True)
    created_at = Column(String(50), nullable=False)
