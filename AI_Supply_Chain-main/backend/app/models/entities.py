from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
)

from app.models.database import Base


class RiskResult(Base):
    __tablename__ = "risk_results"

    id = Column(Integer, primary_key=True, index=True)

    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(100), nullable=False)

    risk_score = Column(Float, nullable=False)
    risk_level = Column(String(20), nullable=False)

    reasons = Column(Text)
    evidence = Column(Text)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class Investigation(Base):
    __tablename__ = "investigations"

    id = Column(Integer, primary_key=True, index=True)

    query = Column(Text, nullable=False)
    intent = Column(String(100))

    agents_used = Column(Text)
    evidence = Column(Text)

    final_answer = Column(Text)

    confidence = Column(Float)

    fallback_used = Column(Boolean, default=False)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id = Column(Integer, primary_key=True, index=True)

    question = Column(Text)

    expected_answer = Column(Text)
    actual_answer = Column(Text)

    answer_correct = Column(Boolean)
    entity_correct = Column(Boolean)
    evidence_grounded = Column(Boolean)
    relevant = Column(Boolean)

    routing_correct = Column(Boolean)

    latency_ms = Column(Float)

    # Phase 6 Dimensions
    expected_behavior = Column(Text, nullable=True)
    actual_behavior = Column(Text, nullable=True)

    planner_correct = Column(Boolean, nullable=True)
    retrieval_correct = Column(Boolean, nullable=True)
    grounding_score = Column(Float, nullable=True)
    relevance_score = Column(Float, nullable=True)
    rbac_correct = Column(Boolean, nullable=True)
    fallback_correct = Column(Boolean, nullable=True)
    audit_complete = Column(Boolean, nullable=True)

    retrieval_mode = Column(String(50), nullable=True)
    evidence_count = Column(Integer, default=0)
    llm_used = Column(Boolean, default=False)
    fallback_used = Column(Boolean, default=False)
    success = Column(Boolean, default=True)

    scope_role = Column(String(50), nullable=True)
    scope_supplier_id = Column(String(50), nullable=True)
    details = Column(Text, nullable=True)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class AuditTrace(Base):
    __tablename__ = "audit_traces"

    id = Column(Integer, primary_key=True, index=True)

    query = Column(Text)

    agent_name = Column(String(100))

    input_data = Column(Text)
    output_data = Column(Text)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    SUPPLY_CHAIN_MANAGER = "SUPPLY_CHAIN_MANAGER"
    SUPPLIER = "SUPPLIER"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, index=True, nullable=False)
    name = Column(String(120), nullable=True)
    email = Column(String(120), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default=UserRole.ADMIN)
    supplier_id = Column(String(100), nullable=True, index=True)
    status = Column(String(30), nullable=False, default="ACTIVE")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Supplier(Base):
    __tablename__ = "suppliers"

    supplier_id = Column(String(100), primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    region = Column(String(100), nullable=False)
    tier = Column(String(50), nullable=False)
    status = Column(String(30), nullable=False, default="ACTIVE")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Product(Base):
    __tablename__ = "products"

    product_id = Column(String(100), primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    unit_cost = Column(Float, nullable=False)
    status = Column(String(30), nullable=False, default="ACTIVE")
    supplier_id = Column(String(100), nullable=True, index=True)
    approval_status = Column(String(30), nullable=False, default="APPROVED")
    approved_by = Column(String(120), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Order(Base):
    __tablename__ = "orders"

    order_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(String(100), nullable=False, index=True)
    supplier_id = Column(String(100), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    order_date = Column(DateTime, default=datetime.utcnow)
    requested_delivery_date = Column(DateTime, nullable=True)
    expected_delivery_date = Column(DateTime, nullable=True)
    actual_delivery_date = Column(DateTime, nullable=True)
    status = Column(String(30), nullable=False, default="PENDING")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(String(100), nullable=False, index=True)
    date = Column(DateTime, nullable=False)
    inventory_level = Column(Integer, nullable=False)
    demand = Column(Integer, nullable=False)
    stockout = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SupplierOffer(Base):
    __tablename__ = "supplier_offers"

    offer_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    supplier_id = Column(String(100), nullable=False, index=True)
    product_id = Column(String(100), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    delivery_days = Column(Integer, nullable=False)
    valid_until = Column(DateTime, nullable=False)
    status = Column(String(30), nullable=False, default="PENDING")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(120), nullable=True)
    