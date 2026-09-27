from typing import Any

from pydantic import BaseModel, Field


class RiskFinding(BaseModel):
    entity_type: str
    entity_id: str

    risk_score: float = Field(
        ge=0,
        le=100
    )

    risk_level: str

    reasons: list[str] = []

    evidence: list[dict[str, Any]] = []


class QueryRequest(BaseModel):
    query: str = Field(
        min_length=3,
        max_length=2000
    )


class QueryResponse(BaseModel):
    answer: str

    intent: str

    confidence: float

    evidence: list[dict[str, Any]] = []

    agents_used: list[str] = []

    fallback_used: bool = False


class Recommendation(BaseModel):
    action: str
    reason: str
    evidence: list[dict[str, Any]] = []


class InvestigationResponse(BaseModel):
    investigation_id: int | None = None

    query: str

    risk_findings: list[RiskFinding] = []

    recommendations: list[Recommendation] = []

    evidence: list[dict[str, Any]] = []

    confidence: float

    agents_used: list[str]

    fallback_used: bool
    