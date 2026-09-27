from __future__ import annotations

import re

from app.query.schema import QueryPlan, QueryRequirement


ALLOWED_METRICS = {
    "total_sales",
    "total_units",
    "total_demand",
    "average_daily_demand",
    "stockout_rate",
    "risk_score",
    "late_rate",
    "delivery_delay",
    "delay_days",
    "lead_time_days",
    "inventory_units",
    "days_of_cover",
    "forecast_demand",
    "anomaly_score",
    "unit_cost",
    "total_orders",
    "product_supplier",
    "supplier_product",
    "product_demand",
    "product_inventory",
    "product_delivery",
    "supplier_offers",
    "summary",
}


ENTITY_TYPES = {
    "product",
    "supplier",
    "route",
    "3pl",
    "order",
    "supply_chain",
}


ALLOWED_OPERATIONS = {
    "rank",
    "compare",
    "summarize",
    "explain",
    "detect_anomaly",
    "forecast",
    "impact_analysis",
    "investigate",
    "lookup",
    "clarify",
}


ALLOWED_DIRECTIONS = {
    "ascending",
    "descending",
    "none",
}


class QueryPlanValidator:

    PRODUCT_PATTERN = re.compile(
        r"^P\d{3,}$",
        re.IGNORECASE,
    )

    SUPPLIER_PATTERN = re.compile(
        r"^S\d{3,}$",
        re.IGNORECASE,
    )

    ROUTE_PATTERN = re.compile(
        r"^R\d{3,}$",
        re.IGNORECASE,
    )

    def validate(
        self,
        plan: QueryPlan,
    ) -> QueryPlan:

        self._validate_metric(
            plan
        )

        self._validate_entity(
            plan
        )

        self._validate_direction(
            plan
        )

        self._validate_operation(
            plan
        )

        self._validate_requirements(
            plan
        )

        plan.confidence = self._safe_confidence(
            plan.confidence
        )

        return plan

    # =========================================================
    # PRIMARY PLAN VALIDATION
    # =========================================================

    def _validate_metric(
        self,
        plan: QueryPlan,
    ) -> None:

        if plan.metric is None:
            return

        plan.metric = (
            str(plan.metric)
            .strip()
            .lower()
        )

        if plan.metric not in ALLOWED_METRICS:

            plan.metric = None

            plan.operation = "clarify"

            plan.clarification_question = (
                "I could not identify a supported "
                "supply-chain metric from your question. "
                "Could you specify what you want to measure?"
            )

    def _validate_entity(
        self,
        plan: QueryPlan,
    ) -> None:

        if plan.entity is None:
            return

        plan.entity = (
            str(plan.entity)
            .lower()
            .strip()
        )

        if plan.entity not in ENTITY_TYPES:

            plan.entity = None
            plan.entity_id = None

            return

        if plan.entity_id is not None:

            plan.entity_id = (
                str(plan.entity_id)
                .strip()
                .upper()
            )

            if not self._valid_entity_id(
                plan.entity,
                plan.entity_id,
            ):
                plan.entity_id = None

    def _validate_direction(
        self,
        plan: QueryPlan,
    ) -> None:

        if plan.direction not in ALLOWED_DIRECTIONS:
            plan.direction = "none"

    def _validate_operation(
        self,
        plan: QueryPlan,
    ) -> None:

        if plan.operation not in ALLOWED_OPERATIONS:
            plan.operation = "clarify"

        if (
            plan.operation == "rank"
            and not plan.metric
        ):

            plan.operation = "clarify"

            plan.clarification_question = (
                "I can rank the data, but I need "
                "to know which metric you want "
                "to rank by."
            )

        if plan.operation == "clarify":

            plan.confidence = min(
                plan.confidence,
                0.60,
            )

    # =========================================================
    # REQUIREMENT VALIDATION
    # =========================================================

    def _validate_requirements(
        self,
        plan: QueryPlan,
    ) -> None:

        if not plan.requirements:
            return

        validated: list[QueryRequirement] = []

        for index, requirement in enumerate(
            plan.requirements
        ):

            if not isinstance(
                requirement,
                QueryRequirement,
            ):
                continue

            self._validate_requirement(
                requirement=requirement,
                index=index,
            )

            if (
                requirement.domain is None
                and requirement.metric is None
            ):
                continue

            validated.append(
                requirement
            )

        plan.requirements = validated

        # Multiple analytical requirements require reasoning.
        if len(plan.requirements) > 1:
            plan.requires_reasoning = True

    def _validate_requirement(
        self,
        requirement: QueryRequirement,
        index: int,
    ) -> None:

        # -----------------------------------------------------
        # Domain
        # -----------------------------------------------------

        if requirement.domain is not None:

            requirement.domain = (
                str(
                    requirement.domain
                )
                .strip()
                .lower()
            )

        # -----------------------------------------------------
        # Operation
        # -----------------------------------------------------

        requirement.operation = (
            str(
                requirement.operation
                or "lookup"
            )
            .strip()
            .lower()
        )

        if (
            requirement.operation
            not in ALLOWED_OPERATIONS
        ):
            requirement.operation = "lookup"

        # -----------------------------------------------------
        # Metric
        # -----------------------------------------------------

        if requirement.metric is not None:

            requirement.metric = (
                str(
                    requirement.metric
                )
                .strip()
                .lower()
            )

            if (
                requirement.metric
                not in ALLOWED_METRICS
            ):
                requirement.metric = None

        # -----------------------------------------------------
        # Direction
        # -----------------------------------------------------

        requirement.direction = (
            str(
                requirement.direction
                or "none"
            )
            .strip()
            .lower()
        )

        if (
            requirement.direction
            not in ALLOWED_DIRECTIONS
        ):
            requirement.direction = "none"

        # -----------------------------------------------------
        # Entity
        # -----------------------------------------------------

        if requirement.entity is not None:

            requirement.entity = (
                str(
                    requirement.entity
                )
                .strip()
                .lower()
            )

        # -----------------------------------------------------
        # Entity ID
        # -----------------------------------------------------

        if requirement.entity_id is not None:

            requirement.entity_id = (
                str(
                    requirement.entity_id
                )
                .strip()
                .upper()
            )

            if (
                requirement.entity
                and requirement.entity
                in ENTITY_TYPES
            ):

                if not self._valid_entity_id(
                    requirement.entity,
                    requirement.entity_id,
                ):
                    requirement.entity_id = None

        # -----------------------------------------------------
        # Relationship
        # -----------------------------------------------------

        if requirement.relationship is not None:

            requirement.relationship = (
                str(
                    requirement.relationship
                )
                .strip()
                .lower()
            )

        # -----------------------------------------------------
        # Filters
        # -----------------------------------------------------

        if not isinstance(
            requirement.filters,
            dict,
        ):
            requirement.filters = {}

        # -----------------------------------------------------
        # Dependency
        #
        # A requirement may depend only on an earlier
        # requirement.
        # -----------------------------------------------------

        if requirement.depends_on is not None:

            try:
                dependency = int(
                    requirement.depends_on
                )
            except (
                TypeError,
                ValueError,
            ):
                dependency = None

            if (
                dependency is None
                or dependency < 0
                or dependency >= index
            ):
                requirement.depends_on = None
            else:
                requirement.depends_on = dependency

        # -----------------------------------------------------
        # Confidence
        # -----------------------------------------------------

        requirement.confidence = (
            self._safe_confidence(
                requirement.confidence
            )
        )

        # -----------------------------------------------------
        # Rank without metric
        # -----------------------------------------------------

        if (
            requirement.operation == "rank"
            and not requirement.metric
        ):
            requirement.operation = "clarify"

    # =========================================================
    # ENTITY ID VALIDATION
    # =========================================================

    def _valid_entity_id(
        self,
        entity: str,
        entity_id: str,
    ) -> bool:

        if entity == "product":
            return bool(
                self.PRODUCT_PATTERN.match(
                    entity_id
                )
            )

        if entity == "supplier":
            return bool(
                self.SUPPLIER_PATTERN.match(
                    entity_id
                )
            )

        if entity == "route":
            return bool(
                self.ROUTE_PATTERN.match(
                    entity_id
                )
            )

        if entity == "3pl":
            return True

        if entity == "order":
            return True

        return False

    # =========================================================
    # CONFIDENCE
    # =========================================================

    @staticmethod
    def _safe_confidence(
        value: float,
    ) -> float:

        try:
            value = float(
                value
            )
        except (
            TypeError,
            ValueError,
        ):
            return 0.0

        return max(
            0.0,
            min(
                1.0,
                value,
            ),
        )