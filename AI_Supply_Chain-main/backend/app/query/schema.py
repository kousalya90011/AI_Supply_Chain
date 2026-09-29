from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# =========================================================
# TYPES
# =========================================================

Domain = Literal[
    "product",
    "supplier",
    "inventory",
    "delivery",
    "route",
    "demand",
    "forecast",
    "order",
    "supply_chain",
    "dashboard",
    "offers",
]


Operation = Literal[
    "rank",
    "compare",
    "summarize",
    "explain",
    "detect_anomaly",
    "forecast",
    "impact_analysis",
    "investigate",
    "lookup",
    "filter",
    "clarify",
]


Direction = Literal[
    "ascending",
    "descending",
    "none",
]


# =========================================================
# ANALYTICAL REQUIREMENT
# =========================================================

class QueryRequirement(BaseModel):
    """
    One analytical requirement extracted from the user's query.

    Example:

        "expensive products with high demand"

    becomes:

        Requirement(
            domain="product",
            metric="unit_cost",
            operation="rank"
        )

        Requirement(
            domain="demand",
            metric="total_demand",
            operation="lookup"
        )
    """

    domain: str | None = None

    operation: str = "lookup"

    metric: str | None = None

    direction: str = "none"

    entity: str | None = None

    entity_id: str | None = None

    relationship: str | None = None

    depends_on: int | None = None

    filters: dict[str, Any] = Field(
        default_factory=dict
    )

    condition: str | None = None

    negative_condition: bool = False

    threshold: dict[str, Any] | None = None

    trend: str | None = None

    comparison: dict[str, Any] | None = None

    aggregation: str | None = None

    entity_ids: list[str] = Field(
        default_factory=list
    )

    scope: str | None = None

    driver: str | None = None

    topic: str | None = None

    purpose: str | None = None

    confidence: float = 0.0


# =========================================================
# QUERY PLAN
# =========================================================

class QueryPlan(BaseModel):

    # -----------------------------------------------------
    # Primary requirement
    # -----------------------------------------------------

    domain: Domain | None = None

    operation: Operation = "clarify"

    metric: str | None = None

    direction: Direction = "none"

    entity: str | None = None

    entity_id: str | None = None

    entity_ids: list[str] = Field(
        default_factory=list
    )

    filters: dict[str, Any] = Field(
        default_factory=dict
    )

    condition: str | None = None

    negative_condition: bool = False

    threshold: dict[str, Any] | None = None

    trend: str | None = None

    scope: str | None = None

    aggregation: str | None = None

    driver: str | None = None

    topic: str | None = None

    time_range: dict[str, Any] | None = None

    comparison: dict[str, Any] | None = None

    # -----------------------------------------------------
    # Dynamic multi-requirement execution
    # -----------------------------------------------------

    requirements: list[QueryRequirement] = Field(
        default_factory=list
    )

    # -----------------------------------------------------
    # Reasoning
    # -----------------------------------------------------

    requires_reasoning: bool = False

    confidence: float = 0.0

    clarification_question: str | None = None

    # -----------------------------------------------------
    # Original query
    # -----------------------------------------------------

    original_query: str = ""

    planner_method: str = "unknown"

    # -----------------------------------------------------
    # Backward-compatible secondary fields
    # -----------------------------------------------------

    secondary_domain: str | None = None

    secondary_operation: str | None = None

    secondary_metric: str | None = None

    relationship: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

