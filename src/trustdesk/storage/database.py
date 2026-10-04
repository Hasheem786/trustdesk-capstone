import json
from pathlib import Path
from typing import Optional
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.trustdesk.config import settings
from src.trustdesk.models.db_models import (
    Base,
    CustomerModel,
    OrderModel,
    KnowledgeDocumentModel,
)

engine = create_engine(
    settings.db_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.db_url else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_context():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
    seed_initial_data()

def seed_initial_data(session: Optional[Session] = None):
    if session is not None:
        _populate_seed_data(session)
    else:
        with get_db_context() as db:
            _populate_seed_data(db)

def _populate_seed_data(db: Session):
    # Seed Customers if empty
    if db.query(CustomerModel).count() == 0 and settings.customers_path.exists():
        with open(settings.customers_path, "r", encoding="utf-8") as f:
            customers_data = json.load(f)
            for c in customers_data:
                db.add(CustomerModel(
                    id=c["id"],
                    name=c["name"],
                    email=c["email"],
                    tier=c.get("tier", "standard"),
                    created_at=c["created_at"]
                ))

    # Seed Orders if empty
    if db.query(OrderModel).count() == 0 and settings.orders_path.exists():
        with open(settings.orders_path, "r", encoding="utf-8") as f:
            orders_data = json.load(f)
            for o in orders_data:
                db.add(OrderModel(
                    id=o["id"],
                    customer_id=o["customer_id"],
                    items_json=json.dumps(o.get("items", [])),
                    total_amount=float(o.get("total_amount", 0.0)),
                    status=o.get("status", "delivered"),
                    order_date=o["order_date"],
                    delivered_date=o.get("delivered_date"),
                    tracking_number=o.get("tracking_number")
                ))

    # Seed KB Documents if empty
    if db.query(KnowledgeDocumentModel).count() == 0 and settings.kb_path.exists():
        with open(settings.kb_path, "r", encoding="utf-8") as f:
            kb_data = json.load(f)
            for doc in kb_data:
                db.add(KnowledgeDocumentModel(
                    doc_id=doc["doc_id"],
                    title=doc["title"],
                    category=doc["category"],
                    tags_json=json.dumps(doc.get("tags", [])),
                    content=doc["content"],
                    is_active=doc.get("is_active", True)
                ))

    db.commit()
