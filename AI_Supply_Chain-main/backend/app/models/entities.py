from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text
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
    