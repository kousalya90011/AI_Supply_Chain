from __future__ import annotations

from typing import Any, TypedDict


class SupplyChainState(TypedDict, total=False):

    # ---------------------------------------------------------
    # USER INPUT
    # ---------------------------------------------------------

    query: str

    # ---------------------------------------------------------
    # QUERY UNDERSTANDING
    # ---------------------------------------------------------

    intent: str
    entity_type: str | None
    entity_id: str | None
    metric: str | None
    scope: str | None
    complexity: str | None
    requires_entity: bool

    # ---------------------------------------------------------
    # AGENT EXECUTION
    # ---------------------------------------------------------

    agent_result: dict[str, Any]

    findings: list[dict[str, Any]]
    evidence: list[dict[str, Any]]

    # ---------------------------------------------------------
    # LLM INSIGHT
    # ---------------------------------------------------------

    insight: dict[str, Any]

    answer: str
    confidence: float

    # ---------------------------------------------------------
    # RECOMMENDATIONS
    # ---------------------------------------------------------

    recommendations: list[str]

    # ---------------------------------------------------------
    # EXECUTION TRACE
    # ---------------------------------------------------------

    agents_used: list[str]

    # ---------------------------------------------------------
    # FALLBACK
    # ---------------------------------------------------------

    fallback_used: bool
    fallback_reason: str | None

    # ---------------------------------------------------------
    # FINAL RESPONSE
    # ---------------------------------------------------------

    status: str
    latency_ms: float