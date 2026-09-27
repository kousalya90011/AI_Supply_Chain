from __future__ import annotations

import re
from typing import Any

from app.llm.query_classifier import QueryClassifier
from app.query.schema import QueryPlan, QueryRequirement


class SemanticQueryPlanner:
    """
    Converts a natural-language query into a validated QueryPlan.

    Architecture
    ------------

        User Query
             ↓
        QueryClassifier
             ↓
        Semantic Classification
             ↓
        QueryPlan
             ├── primary fields
             └── requirements[]
                    ├── requirement 0
                    ├── requirement 1
                    ├── requirement 2
                    └── requirement N

    Important architecture decision
    --------------------------------

    QueryClassifier is the ONLY semantic LLM component.

    This planner does NOT call the LLM directly.

    Responsibilities:

        1. Call QueryClassifier.
        2. Convert classification -> QueryPlan.
        3. Preserve classifier requirements.
        4. Extract explicit entity IDs.
        5. Build a backward-compatible primary requirement.
        6. Preserve legacy secondary fields where useful.
        7. Provide a small deterministic fallback.

    There is intentionally NO artificial limit on the number
    of requirements.
    """

    def __init__(self) -> None:
        self.classifier = QueryClassifier()

    # =========================================================
    # PUBLIC API
    # =========================================================

    def plan(self, query: str) -> QueryPlan:
        """
        Convert a natural-language query into a QueryPlan.
        """

        cleaned_query = self._clean_query(query)

        if not cleaned_query:
            return QueryPlan(
                operation="clarify",
                confidence=0.0,
                clarification_question=(
                    "What supply-chain information would you like to know?"
                ),
                original_query=query or "",
                planner_method="empty_query",
            )

        try:
            classification = self.classifier.classify(
                cleaned_query
            )

            if not isinstance(classification, dict):
                classification = {}

            return self._classification_to_plan(
                query=cleaned_query,
                classification=classification,
            )

        except Exception as exc:
            return self._fallback_plan(
                query=cleaned_query,
                error=str(exc),
            )

    # =========================================================
    # CLASSIFICATION -> QUERY PLAN
    # =========================================================

    def _classification_to_plan(
        self,
        query: str,
        classification: dict[str, Any],
    ) -> QueryPlan:

        intent = str(
            classification.get("intent")
            or "unknown"
        ).strip().lower()

        metric = classification.get("metric")

        if metric is not None:
            metric = str(metric).strip().lower()

        confidence = self._safe_float(
            classification.get("confidence"),
            default=0.0,
        )

        method = str(
            classification.get("method")
            or classification.get("planner_method")
            or "llm_semantic"
        )

        # -----------------------------------------------------
        # Entity information
        # -----------------------------------------------------

        entity = classification.get("entity_type")

        if entity is None:
            entity = classification.get("entity")

        if entity is not None:
            entity = str(entity).strip().lower()

        entity_id = classification.get("entity_id")

        if entity_id is None:
            entity_id = self._extract_entity_id(query)

        # -----------------------------------------------------
        # Build primary plan
        # -----------------------------------------------------

        plan = self._build_primary_plan(
            query=query,
            intent=intent,
            metric=metric,
            entity=entity,
            entity_id=entity_id,
            confidence=confidence,
            method=method,
            classification=classification,
        )

        # -----------------------------------------------------
        # Attach semantic requirements
        # -----------------------------------------------------

        self._attach_requirements(
            plan=plan,
            classification=classification,
        )

        return plan

    # =========================================================
    # PRIMARY PLAN
    # =========================================================

    def _build_primary_plan(
        self,
        query: str,
        intent: str,
        metric: str | None,
        entity: str | None,
        entity_id: str | None,
        confidence: float,
        method: str,
        classification: dict[str, Any] | None = None,
    ) -> QueryPlan:

        # -----------------------------------------------------
        # Product sales
        # -----------------------------------------------------

        if intent == "sales_ranking":
            return QueryPlan(
                domain="product",
                operation="rank",
                metric="total_sales",
                direction=self._sales_direction(query),
                entity="product",
                entity_id=entity_id,
                confidence=confidence,
                original_query=query,
                planner_method=method,
            )

        # -----------------------------------------------------
        # Product demand
        # -----------------------------------------------------

        if intent == "demand_ranking":
            return QueryPlan(
                domain="demand",
                operation="rank",
                metric="total_demand",
                direction=self._ranking_direction(
                    query=query,
                    default="descending",
                ),
                entity="product",
                entity_id=entity_id,
                confidence=confidence,
                original_query=query,
                planner_method=method,
            )

        # -----------------------------------------------------
        # Stockout ranking
        # -----------------------------------------------------

        if intent == "stockout_ranking":
            return QueryPlan(
                domain="inventory",
                operation="rank",
                metric="stockout_rate",
                direction="descending",
                entity="product",
                entity_id=entity_id,
                confidence=confidence,
                original_query=query,
                planner_method=method,
            )

        # -----------------------------------------------------
        # Inventory risk
        # -----------------------------------------------------

        if intent == "inventory_risk":

            if entity_id:
                return QueryPlan(
                    domain="inventory",
                    operation="explain",
                    metric="risk_score",
                    direction="none",
                    entity="product",
                    entity_id=entity_id,
                    requires_reasoning=True,
                    confidence=confidence,
                    original_query=query,
                    planner_method=method,
                )

            return QueryPlan(
                domain="inventory",
                operation="rank",
                metric="risk_score",
                direction="descending",
                entity="product",
                entity_id=None,
                requires_reasoning=True,
                confidence=confidence,
                original_query=query,
                planner_method=method,
            )

        # -----------------------------------------------------
        # Supplier relationship lookup
        # -----------------------------------------------------

        if intent == "supplier_relationship_analysis":
            return QueryPlan(
                domain="supplier",
                operation="lookup",
                metric="product_supplier",
                direction="none",
                entity="product",
                entity_id=entity_id,
                confidence=confidence,
                original_query=query,
                planner_method=method,
            )

        # -----------------------------------------------------
        # Order analysis / total orders
        # -----------------------------------------------------

        if intent == "order_analysis":
            return QueryPlan(
                domain="order",
                operation="lookup",
                metric="total_orders",
                direction="none",
                entity=("supplier" if entity == "supplier" else "product"),
                entity_id=entity_id,
                confidence=confidence,
                original_query=query,
                planner_method=method,
            )

        # -----------------------------------------------------
        # Supplier risk
        # -----------------------------------------------------

        if intent == "supplier_risk":
            return QueryPlan(
                domain="supplier",
                operation="rank",
                metric="late_rate",
                direction="descending",
                entity="supplier",
                entity_id=entity_id,
                requires_reasoning=True,
                confidence=confidence,
                original_query=query,
                planner_method=method,
            )

        # -----------------------------------------------------
        # Delivery risk
        # -----------------------------------------------------

        if intent == "delivery_risk":
            return QueryPlan(
                domain="delivery",
                operation="rank",
                metric="delivery_delay",
                direction="descending",
                entity="3pl",
                entity_id=entity_id,
                confidence=confidence,
                original_query=query,
                planner_method=method,
            )

        # -----------------------------------------------------
        # Route risk
        # -----------------------------------------------------

        if intent == "route_risk":
            return QueryPlan(
                domain="route",
                operation="rank",
                metric="risk_score",
                direction="descending",
                entity="route",
                entity_id=entity_id,
                requires_reasoning=True,
                confidence=confidence,
                original_query=query,
                planner_method=method,
            )

        # -----------------------------------------------------
        # Forecast
        # -----------------------------------------------------

        if intent == "forecast":
            return QueryPlan(
                domain="forecast",
                operation="forecast",
                metric="forecast_demand",
                direction="none",
                entity="product",
                entity_id=entity_id,
                requires_reasoning=True,
                confidence=confidence,
                original_query=query,
                planner_method=method,
            )

        # -----------------------------------------------------
        # Anomaly detection
        # -----------------------------------------------------

        if intent == "anomaly_detection":
            return QueryPlan(
                domain="order",
                operation="detect_anomaly",
                metric="anomaly_score",
                direction="descending",
                entity="order",
                entity_id=entity_id,
                requires_reasoning=True,
                confidence=confidence,
                original_query=query,
                planner_method=method,
            )

        # -----------------------------------------------------
        # Dashboard
        # -----------------------------------------------------

        if intent == "dashboard":
            return QueryPlan(
                domain="dashboard",
                operation="summarize",
                metric="summary",
                direction="none",
                entity="supply_chain",
                entity_id=None,
                requires_reasoning=True,
                confidence=confidence,
                original_query=query,
                planner_method=method,
            )

        # -----------------------------------------------------
        # Complex supply-chain reasoning
        # -----------------------------------------------------

        if intent == "complex_risk":
            return QueryPlan(
                domain="supply_chain",
                operation="impact_analysis",
                metric="summary",
                direction="none",
                entity=entity or "supply_chain",
                entity_id=entity_id,
                requires_reasoning=True,
                confidence=confidence,
                original_query=query,
                planner_method=method,
            )

        # -----------------------------------------------------
        # Ambiguous product question
        # -----------------------------------------------------

        if intent == "ambiguous_product_ranking":
            return QueryPlan(
                domain="product",
                operation="clarify",
                metric=None,
                direction="none",
                entity="product",
                entity_id=entity_id,
                confidence=min(confidence, 0.60),
                clarification_question=(
                    "What would you like to rank products by — "
                    "sales, demand, unit cost, inventory risk, "
                    "or stockout risk?"
                ),
                original_query=query,
                planner_method=method,
            )

        # -----------------------------------------------------
        # Product cost
        # -----------------------------------------------------

        if intent == "product_cost_ranking":

            direction = self._cost_direction(query)

            return QueryPlan(
                domain="product",
                operation="rank",
                metric="unit_cost",
                direction=direction,
                entity="product",
                entity_id=entity_id,
                confidence=confidence,
                original_query=query,
                planner_method=method,
            )

        # -----------------------------------------------------
        # Multi-requirement query
        # -----------------------------------------------------

        if intent == "multi_requirement":

            requirements = (
                classification.get("requirements", [])
                if isinstance(classification, dict)
                else []
            )

            if isinstance(requirements, list) and requirements:
                first = requirements[0]

                if isinstance(first, dict):
                    primary = self._build_requirement(
                        raw_requirement=first,
                        index=0,
                        plan=QueryPlan(
                            domain=(first.get("domain") or "product"),
                            operation=(first.get("operation") or "rank"),
                            metric=first.get("metric"),
                            direction=(first.get("direction") or "none"),
                            entity=(first.get("entity") or "product"),
                            entity_id=(first.get("entity_id") or entity_id),
                            original_query=query,
                            planner_method=method,
                        ),
                    )

                    if primary is not None:
                        return QueryPlan(
                            domain=primary.domain or "product",
                            operation=primary.operation or "rank",
                            metric=primary.metric,
                            direction=primary.direction or "none",
                            entity=primary.entity or "product",
                            entity_id=primary.entity_id or entity_id,
                            confidence=confidence,
                            original_query=query,
                            planner_method=method,
                        )

        # -----------------------------------------------------
        # Unknown
        # -----------------------------------------------------

        return QueryPlan(
            domain=None,
            operation="clarify",
            metric=None,
            direction="none",
            entity=entity,
            entity_id=entity_id,
            confidence=min(confidence, 0.60),
            clarification_question=(
                "Could you clarify what supply-chain information "
                "you want to analyze?"
            ),
            original_query=query,
            planner_method=method,
        )

    # =========================================================
    # REQUIREMENTS
    # =========================================================

    def _attach_requirements(
        self,
        plan: QueryPlan,
        classification: dict[str, Any],
    ) -> None:
        """
        Attach the semantic requirement list produced by the
        QueryClassifier.

        There is intentionally no maximum number of requirements.

        Example:

            User:
            "Which products have high demand, who supplies them,
             how many orders did we have, and what is their
             inventory?"

            requirements:

                0 -> product demand
                1 -> product supplier
                2 -> product orders
                3 -> product inventory
        """

        raw_requirements = classification.get(
            "requirements"
        )

        requirements: list[QueryRequirement] = []

        if isinstance(raw_requirements, list):

            for index, raw_requirement in enumerate(
                raw_requirements
            ):

                if not isinstance(
                    raw_requirement,
                    dict,
                ):
                    continue

                requirement = self._build_requirement(
                    raw_requirement=raw_requirement,
                    index=index,
                    plan=plan,
                )

                if requirement is not None:
                    requirements.append(
                        requirement
                    )

        # -----------------------------------------------------
        # If classifier produced no requirements, preserve
        # the primary plan as requirement 0.
        # -----------------------------------------------------

        if not requirements:

            if plan.operation != "clarify" and plan.metric:

                requirements.append(
                    self._requirement_from_plan(
                        plan
                    )
                )

        # -----------------------------------------------------
        # If requirements exist but primary requirement is
        # missing, do NOT silently create duplicate work.
        #
        # The classifier's requirements are treated as the
        # semantic source of truth.
        # -----------------------------------------------------

        plan.requirements = requirements

        # Multiple requirements imply reasoning.
        if len(requirements) > 1:
            plan.requires_reasoning = True

        # -----------------------------------------------------
        # Backward compatibility
        #
        # Older QueryService / frontend code may still inspect
        # secondary_* fields.
        #
        # These fields are NOT used for actual execution.
        # -----------------------------------------------------

        self._populate_legacy_secondary_fields(
            plan
        )

    # =========================================================
    # BUILD REQUIREMENT
    # =========================================================

    def _build_requirement(
        self,
        raw_requirement: dict[str, Any],
        index: int,
        plan: QueryPlan,
    ) -> QueryRequirement | None:

        domain = raw_requirement.get(
            "domain"
        )

        operation = raw_requirement.get(
            "operation"
        ) or "lookup"

        metric = raw_requirement.get(
            "metric"
        )

        direction = raw_requirement.get(
            "direction"
        ) or "none"

        entity = raw_requirement.get(
            "entity"
        )

        entity_id = raw_requirement.get(
            "entity_id"
        )

        relationship = raw_requirement.get(
            "relationship"
        )

        depends_on = raw_requirement.get(
            "depends_on"
        )

        filters = raw_requirement.get(
            "filters"
        )

        purpose = raw_requirement.get(
            "purpose"
        )

        confidence = self._safe_float(
            raw_requirement.get(
                "confidence"
            ),
            default=plan.confidence,
        )

        # -----------------------------------------------------
        # Normalize strings
        # -----------------------------------------------------

        if domain is not None:
            domain = str(
                domain
            ).strip().lower()

        operation = str(
            operation
        ).strip().lower()

        if metric is not None:
            metric = str(
                metric
            ).strip().lower()

        direction = str(
            direction
        ).strip().lower()

        if direction not in {
            "ascending",
            "descending",
            "none",
        }:
            direction = "none"

        if entity is not None:
            entity = str(
                entity
            ).strip().lower()

        if entity_id is not None:
            entity_id = str(
                entity_id
            ).strip().upper()

        if relationship is not None:
            relationship = str(
                relationship
            ).strip().lower()

        # -----------------------------------------------------
        # Validate dependency index.
        #
        # A requirement may only depend on an earlier
        # requirement.
        # -----------------------------------------------------

        if depends_on is not None:

            try:
                depends_on = int(
                    depends_on
                )
            except (
                TypeError,
                ValueError,
            ):
                depends_on = None

            if (
                depends_on is not None
                and (
                    depends_on < 0
                    or depends_on >= index
                )
            ):
                depends_on = None

        # -----------------------------------------------------
        # Filters
        # -----------------------------------------------------

        if not isinstance(
            filters,
            dict,
        ):
            filters = {}

        # -----------------------------------------------------
        # First requirement can inherit explicit entity ID.
        #
        # Example:
        #
        # "What is the risk of P00003 and who supplies it?"
        # -----------------------------------------------------

        if (
            index == 0
            and entity_id is None
            and plan.entity_id is not None
        ):
            entity_id = plan.entity_id

        # -----------------------------------------------------
        # Ignore completely empty requirement.
        # -----------------------------------------------------

        if (
            domain is None
            and metric is None
            and relationship is None
        ):
            return None

        return QueryRequirement(
            domain=domain,
            operation=operation,
            metric=metric,
            direction=direction,
            entity=entity,
            entity_id=entity_id,
            relationship=relationship,
            depends_on=depends_on,
            filters=filters,
            purpose=purpose,
            confidence=confidence,
        )

    # =========================================================
    # REQUIREMENT FROM PRIMARY PLAN
    # =========================================================

    @staticmethod
    def _requirement_from_plan(
        plan: QueryPlan,
    ) -> QueryRequirement:

        return QueryRequirement(
            domain=plan.domain,
            operation=plan.operation,
            metric=plan.metric,
            direction=plan.direction,
            entity=plan.entity,
            entity_id=plan.entity_id,
            relationship=None,
            depends_on=None,
            filters=dict(plan.filters or {}),
            purpose="Primary analytical requirement",
            confidence=plan.confidence,
        )

    # =========================================================
    # LEGACY SECONDARY FIELDS
    # =========================================================

    @staticmethod
    def _populate_legacy_secondary_fields(
        plan: QueryPlan,
    ) -> None:
        """
        Preserve the old secondary_* fields only so older
        application code does not immediately break.

        Actual execution must use plan.requirements.
        """

        if len(plan.requirements) < 2:
            return

        second = plan.requirements[1]

        plan.secondary_domain = second.domain
        plan.secondary_operation = second.operation
        plan.secondary_metric = second.metric
        plan.relationship = second.relationship

    # =========================================================
    # DIRECTION HELPERS
    # =========================================================

    def _cost_direction(
        self,
        query: str,
    ) -> str:

        normalized = self._normalize(
            query
        )

        low_cost_signals = (
            "cheap",
            "cheapest",
            "low cost",
            "lowest cost",
            "less costly",
            "least costly",
            "affordable",
            "budget",
            "inexpensive",
            "won't cost much",
            "will not cost much",
            "cost less",
            "lower cost",
        )

        high_cost_signals = (
            "expensive",
            "most expensive",
            "highest cost",
            "high cost",
            "cost more",
            "costlier",
            "premium",
            "high priced",
            "higher priced",
        )

        if any(
            signal in normalized
            for signal in low_cost_signals
        ):
            return "ascending"

        if any(
            signal in normalized
            for signal in high_cost_signals
        ):
            return "descending"

        return "descending"

    def _sales_direction(
        self,
        query: str,
    ) -> str:

        return self._ranking_direction(
            query=query,
            default="descending",
        )

    def _ranking_direction(
        self,
        query: str,
        default: str = "descending",
    ) -> str:

        normalized = self._normalize(
            query
        )

        ascending_signals = (
            "least",
            "lowest",
            "smallest",
            "minimum",
            "fewest",
            "least sold",
            "lowest sales",
            "lowest demand",
            "least demand",
        )

        descending_signals = (
            "most",
            "highest",
            "largest",
            "maximum",
            "greatest",
            "top",
            "best",
            "highest sales",
            "highest demand",
        )

        if any(
            signal in normalized
            for signal in ascending_signals
        ):
            return "ascending"

        if any(
            signal in normalized
            for signal in descending_signals
        ):
            return "descending"

        return default

    # =========================================================
    # ENTITY EXTRACTION
    # =========================================================

    @staticmethod
    def _extract_entity_id(
        query: str,
    ) -> str | None:

        match = re.search(
            r"\b(P\d{3,}|S\d{3,}|R\d{3,})\b",
            query.upper(),
        )

        if match:
            return match.group(1)

        return None

    # =========================================================
    # FALLBACK
    # =========================================================

    def _fallback_plan(
        self,
        query: str,
        error: str,
    ) -> QueryPlan:

        normalized = self._normalize(
            query
        )

        entity_id = self._extract_entity_id(
            query
        )

        # -----------------------------------------------------
        # Product cost
        # -----------------------------------------------------

        if self._looks_like_cost_query(
            normalized
        ):

            plan = QueryPlan(
                domain="product",
                operation="rank",
                metric="unit_cost",
                direction=self._cost_direction(
                    normalized
                ),
                entity="product",
                entity_id=entity_id,
                confidence=0.70,
                original_query=query,
                planner_method="deterministic_fallback",
            )

            plan.requirements = [
                self._requirement_from_plan(
                    plan
                )
            ]

            return plan

        # -----------------------------------------------------
        # Sales
        # -----------------------------------------------------

        if any(
            word in normalized
            for word in (
                "sales",
                "revenue",
                "sold",
            )
        ):

            plan = QueryPlan(
                domain="product",
                operation="rank",
                metric="total_sales",
                direction=self._sales_direction(
                    normalized
                ),
                entity="product",
                entity_id=entity_id,
                confidence=0.65,
                original_query=query,
                planner_method="deterministic_fallback",
            )

            plan.requirements = [
                self._requirement_from_plan(
                    plan
                )
            ]

            return plan

        # -----------------------------------------------------
        # Demand
        # -----------------------------------------------------

        if "demand" in normalized:

            plan = QueryPlan(
                domain="demand",
                operation="rank",
                metric="total_demand",
                direction=self._ranking_direction(
                    normalized,
                    "descending",
                ),
                entity="product",
                entity_id=entity_id,
                confidence=0.65,
                original_query=query,
                planner_method="deterministic_fallback",
            )

            plan.requirements = [
                self._requirement_from_plan(
                    plan
                )
            ]

            return plan

        # -----------------------------------------------------
        # Stockout
        # -----------------------------------------------------

        if any(
            phrase in normalized
            for phrase in (
                "stockout",
                "stock out",
                "out of stock",
            )
        ):

            plan = QueryPlan(
                domain="inventory",
                operation="rank",
                metric="stockout_rate",
                direction="descending",
                entity="product",
                entity_id=entity_id,
                confidence=0.65,
                original_query=query,
                planner_method="deterministic_fallback",
            )

            plan.requirements = [
                self._requirement_from_plan(
                    plan
                )
            ]

            return plan

        # -----------------------------------------------------
        # Supplier
        # -----------------------------------------------------

        if "supplier" in normalized:

            plan = QueryPlan(
                domain="supplier",
                operation="rank",
                metric="late_rate",
                direction="descending",
                entity="supplier",
                entity_id=entity_id,
                confidence=0.60,
                original_query=query,
                planner_method="deterministic_fallback",
            )

            plan.requirements = [
                self._requirement_from_plan(
                    plan
                )
            ]

            return plan

        # -----------------------------------------------------
        # Unknown
        # -----------------------------------------------------

        return QueryPlan(
            domain=None,
            operation="clarify",
            metric=None,
            direction="none",
            entity=None,
            entity_id=entity_id,
            confidence=0.30,
            clarification_question=(
                "Could you clarify whether you want to analyze "
                "sales, demand, inventory, suppliers, delivery, "
                "forecasting, cost, or another supply-chain metric?"
            ),
            original_query=query,
            planner_method="deterministic_fallback",
        )

    # =========================================================
    # COST FALLBACK DETECTION
    # =========================================================

    @staticmethod
    def _looks_like_cost_query(
        query: str,
    ) -> bool:

        cost_signals = (
            "cost",
            "cheap",
            "cheapest",
            "affordable",
            "inexpensive",
            "expensive",
            "premium",
            "priced",
            "price",
            "budget",
        )

        return any(
            signal in query
            for signal in cost_signals
        )

    # =========================================================
    # TEXT HELPERS
    # =========================================================

    @staticmethod
    def _clean_query(
        query: str,
    ) -> str:

        if query is None:
            return ""

        return " ".join(
            str(query).strip().split()
        )

    @staticmethod
    def _normalize(
        text: str,
    ) -> str:

        return " ".join(
            str(text)
            .lower()
            .strip()
            .split()
        )

    @staticmethod
    def _safe_float(
        value: Any,
        default: float = 0.0,
    ) -> float:

        try:

            result = float(value)

            if result < 0:
                return default

            if result > 1:
                return 1.0

            return result

        except (
            TypeError,
            ValueError,
        ):
            return default