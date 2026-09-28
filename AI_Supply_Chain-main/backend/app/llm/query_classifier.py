from __future__ import annotations

import json
import re
from typing import Any

from app.llm.client import LLMClient


class QueryClassifier:
    """
    Single semantic query classifier for the application.

    Responsibility:

        Natural-language query
                ↓
        Semantic classification
                ↓
        Structured classification
                ↓
        One or more analytical requirements

    This class does NOT execute analytics.
    It does NOT calculate business metrics.

    It only determines what the user is asking.

    The classifier supports both:

    1. Simple queries

        "Which products have the highest demand?"

    2. Multi-requirement queries

        "Which products have high demand, who supplies them,
         and how many orders did we have for those products?"

    Example output:

        {
            "intent": "multi_requirement",
            "requirements": [
                {
                    "domain": "demand",
                    "operation": "rank",
                    "metric": "total_demand",
                    "direction": "descending",
                    "entity": "product",
                    "depends_on": null
                },
                {
                    "domain": "supplier",
                    "operation": "lookup",
                    "metric": "product_supplier",
                    "direction": "none",
                    "entity": "product",
                    "depends_on": 0
                },
                {
                    "domain": "order",
                    "operation": "lookup",
                    "metric": "total_orders",
                    "direction": "none",
                    "entity": "product",
                    "depends_on": 0
                }
            ]
        }

    The important design principle is:

        Query understanding is dynamic.

    We do NOT limit the query to only one or two
    secondary requirements.
    """

    # =========================================================
    # ALLOWED INTENTS
    # =========================================================

    ALLOWED_INTENTS = {
        "sales_ranking",
        "demand_ranking",
        "stockout_ranking",
        "inventory_risk",
        "supplier_risk",
        "delivery_risk",
        "route_risk",
        "forecast",
        "anomaly_detection",
        "dashboard",
        "complex_risk",
        "ambiguous_product_ranking",
        "product_cost_ranking",
        "order_analysis",
        "multi_requirement",
        "product_disruption_impact",
        "lead_time_anomaly",
        "supplier_investigation",
        "major_risks",
        "supplier_delivery_risk",
        "supplier_inventory_impact",
        "unknown",
    }

    # =========================================================
    # ALLOWED METRICS
    # =========================================================

    ALLOWED_METRICS = {
        "total_sales",
        "total_units",
        "total_demand",
        "average_daily_demand",
        "stockout_rate",
        "risk_score",
        "delivery_delay",
        "delay_days",
        "lead_time_days",
        "inventory_units",
        "days_of_cover",
        "forecast_demand",
        "anomaly_score",
        "unit_cost",
        "summary",
        "total_orders",
        "product_supplier",
        "supplier_product",
        "product_demand",
        "product_inventory",
        "product_delivery",
        "supplier_offers",
        "lead_time_anomaly",
        "supplier_disruption_impact",
        "major_risks",
        "supplier_investigation",
        "supplier_inventory_impact",
        "late_rate",
        None,
    }

    # =========================================================
    # ALLOWED SCOPES
    # =========================================================

    ALLOWED_SCOPES = {
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
        "3pl",
        "offers",
        None,
    }

    # =========================================================
    # ALLOWED OPERATIONS
    # =========================================================

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

    # =========================================================
    # INITIALIZATION
    # =========================================================

    def __init__(self) -> None:
        self.llm = LLMClient()

    # =========================================================
    # PUBLIC CLASSIFICATION METHOD
    # =========================================================

    def classify(
        self,
        query: str,
    ) -> dict[str, Any]:

        original_query = (
            query or ""
        ).strip()

        # -----------------------------------------------------
        # Empty query
        # -----------------------------------------------------

        if not original_query:
            return {
                "intent": "unknown",
                "metric": None,
                "scope": None,
                "complexity": "simple",
                "requires_entity": False,
                "confidence": 0.0,
                "requirements": [],
                "method": "fallback",
            }

        normalized = self._normalize(
            original_query
        )

        # -----------------------------------------------------
        # Explicit entity extraction
        # -----------------------------------------------------

        entity_type, entity_id = (
            self._extract_entity(
                original_query
            )
        )

        # -----------------------------------------------------
        # Ambiguous product ranking
        # -----------------------------------------------------

        if self._is_ambiguous_product_query(
            normalized
        ):

            return {
                "intent": "ambiguous_product_ranking",
                "metric": None,
                "scope": "product",
                "complexity": "simple",
                "requires_entity": False,
                "confidence": 0.60,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "requirements": [],
                "method": "deterministic",
            }

        # =====================================================
        # STRONG MULTI-REQUIREMENT SIGNALS
        # =====================================================

        multi_requirements = self._deterministic_multi_requirements(
            normalized
        )

        if len(multi_requirements) > 1:

            first = multi_requirements[0]

            return {
                "intent": "multi_requirement",
                "metric": first.get("metric"),
                "scope": first.get("domain"),
                "complexity": "complex",
                "requires_entity": False,
                "confidence": 0.72,
                "requirements": multi_requirements,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "method": "deterministic_fallback",
            }

        # =====================================================
        # PRIMARY LLM CLASSIFICATION
        # =====================================================

        try:

            llm_result = self._llm_classify(
                original_query
            )

            if llm_result:

                validated = self._validate_result(
                    llm_result
                )

                if validated:

                    # Preserve explicit entity IDs.
                    validated["entity_type"] = (
                        entity_type
                        or validated.get(
                            "entity_type"
                        )
                    )

                    validated["entity_id"] = (
                        entity_id
                        or validated.get(
                            "entity_id"
                        )
                    )

                    validated["method"] = "llm"

                    return validated

        except Exception:
            # LLM failure must never crash the
            # query API.
            pass

        # =====================================================
        # DETERMINISTIC FALLBACK
        # =====================================================

        fallback = self._deterministic_classification(
            normalized
        )

        fallback["entity_type"] = entity_type
        fallback["entity_id"] = entity_id
        fallback["method"] = "deterministic_fallback"

        return fallback

    # =========================================================
    # LLM CLASSIFICATION
    # =========================================================

    def _llm_classify(
        self,
        query: str,
    ) -> dict[str, Any] | None:

        messages = [
            {
                "role": "system",
                "content": self._system_prompt(),
            },
            {
                "role": "user",
                "content": query,
            },
        ]

        response = self.llm.generate(
            messages
        )

        if not response:
            return None

        content = response.get(
            "content",
            "",
        )

        if not content:
            return None

        return self._extract_json(
            content
        )

    # =========================================================
    # SYSTEM PROMPT
    # =========================================================

    @staticmethod
    def _system_prompt() -> str:

        return """
You are the semantic query classifier for a professional
Supply Chain Risk Intelligence system.

Your ONLY responsibility is to understand the user's question.

Do NOT:
- calculate analytics
- invent data
- answer the question
- generate recommendations
- generate explanations

The application will execute deterministic analytics after
your classification.

=========================================================
CORE PRINCIPLE
=========================================================

Understand the meaning of the user's request.

Do NOT depend on exact keywords.

A user may express the same requirement in many ways.

For example:

"Which products are cheap?"

"Which products won't cost us much?"

"Which products are affordable?"

"Which products are inexpensive?"

All mean:

product
+
unit_cost
+
ascending ranking

=========================================================
SINGLE VS MULTI REQUIREMENT
=========================================================

A query can contain ONE or MANY analytical requirements.

Simple example:

"Which products have the highest demand?"

This contains ONE requirement.

Multi-requirement example:

"Which products have high demand, who supplies them,
and how many orders did we have for those products?"

This contains THREE requirements.

Another example:

"Which suppliers have the highest delays, which products
do they supply, what is the demand for those products,
and how many orders did we receive?"

This contains FOUR requirements.

Do NOT limit the number of requirements.

Extract ALL meaningful analytical requirements
expressed by the user.

=========================================================
DEPENDENCIES
=========================================================

Requirements can depend on previous requirements.

Example:

"Which products have the highest demand and who supplies them?"

Requirement 0:

{
    "domain": "demand",
    "operation": "rank",
    "metric": "total_demand",
    "direction": "descending",
    "entity": "product",
    "depends_on": null
}

Requirement 1:

{
    "domain": "supplier",
    "operation": "lookup",
    "metric": "product_supplier",
    "direction": "none",
    "entity": "product",
    "depends_on": 0
}

The second requirement means:

"Find suppliers for the products returned by requirement 0."

Another example:

"Which suppliers have the highest delays and which products
do they supply?"

Requirement 0:

supplier
late_rate
rank

Requirement 1:

supplier → product
supplier_product
lookup
depends_on = 0

Another example:

"Which products have high demand, what is their inventory,
who supplies them, and how many orders did we have?"

Requirement 0:
product demand ranking

Requirement 1:
product inventory lookup
depends_on = 0

Requirement 2:
product supplier lookup
depends_on = 0

Requirement 3:
product order count lookup
depends_on = 0

=========================================================
SUPPORTED DOMAINS
=========================================================

product
supplier
inventory
delivery
route
demand
forecast
order
supply_chain
dashboard
3pl

=========================================================
SUPPORTED OPERATIONS
=========================================================

rank
compare
summarize
explain
detect_anomaly
forecast
impact_analysis
investigate
lookup
clarify

=========================================================
SUPPORTED METRICS
=========================================================

total_sales
total_units
total_demand
average_daily_demand
stockout_rate
risk_score
delivery_delay
delay_days
lead_time_days
inventory_units
days_of_cover
forecast_demand
anomaly_score
unit_cost
summary
total_orders
product_supplier
supplier_product
product_demand
product_inventory
product_delivery

=========================================================
SUPPORTED INTENTS
=========================================================

sales_ranking
demand_ranking
stockout_ranking
inventory_risk
supplier_risk
delivery_risk
route_risk
forecast
anomaly_detection
dashboard
complex_risk
ambiguous_product_ranking
product_cost_ranking
multi_requirement
unknown

=========================================================
INTENT DEFINITIONS
=========================================================

sales_ranking

Use when the user wants products ranked by:

- sales
- revenue
- selling performance
- sales volume
- units sold

Examples:

"Which products sell the most?"

"Which product generates the highest revenue?"

"Show our top selling products."

Metric:

total_sales

Scope:

product


=========================================================

demand_ranking

Use when the user wants products ranked by:

- demand
- customer need
- demand volume
- required quantity

Examples:

"Which products are most in demand?"

"What products do customers need the most?"

"Which products have the highest demand?"

Metric:

total_demand

Scope:

product


=========================================================

stockout_ranking

Use when the user asks about:

- stockouts
- running out of stock
- availability problems

Examples:

"Which products keep going out of stock?"

"What products have the worst stockouts?"

"Which products keep running out?"

Metric:

stockout_rate

Scope:

product


=========================================================

inventory_risk

Use when the user asks about:

- inventory risk
- stock risk
- risky products
- inventory exposure
- risk score

Examples:

"Which products are riskiest?"

"Which products have high inventory risk?"

"Why is P00003 risky?"

"What is the inventory risk of P00003?"

Metric:

risk_score

Scope:

product


=========================================================

supplier_risk

Use when the question focuses on:

- supplier performance
- supplier reliability
- supplier delays
- supplier late orders
- supplier risk

Examples:

"Which suppliers have the highest delays?"

"Which suppliers are unreliable?"

"Show supplier performance."

Metric:

late_rate

Scope:

supplier


=========================================================

delivery_risk

Use when the question focuses on delivery/logistics
performance rather than supplier performance.

Examples:

"Which deliveries are most delayed?"

"Which logistics groups have the highest delay?"

"Show delivery delays."

Metric:

delivery_delay

Scope:

delivery


=========================================================

route_risk

Use when the user asks about route risk.

Examples:

"Which routes are risky?"

"Which routes have the highest delays?"

Metric:

risk_score

Scope:

route


=========================================================

forecast
=========================================================

Use for future-oriented questions.

Examples:

"What will demand look like next week?"

"Forecast P00003."

"What is the expected demand?"

Metric:

forecast_demand

Scope:

forecast or product


=========================================================

anomaly_detection
=========================================================

Use for unusual or abnormal operational behavior.

Examples:

"Identify unusual supplier lead times."

"Are there abnormal delivery delays?"

"Which lead times are unusual?"

Metric:

anomaly_score


=========================================================

dashboard
=========================================================

Use for broad supply-chain summaries.

Examples:

"What are the major supply chain risks?"

"Give me an overview."

"Summarize the current supply chain."

Metric:

summary

Scope:

dashboard


=========================================================

complex_risk
=========================================================

Use when the user asks for causal or impact reasoning.

Examples:

"How could a supplier delay affect inventory?"

"What happens to inventory if supplier delays continue?"

"Which supplier problems could cause stockouts?"

Scope:

supply_chain

=========================================================
PRODUCT COST
=========================================================

Use product_cost_ranking whenever the user wants products
compared according to unit cost.

Examples:

"Which products are cheap?"

"Which products are affordable?"

"Which products won't cost us much?"

"Which products are inexpensive?"

"Which products cost more?"

"Which products are expensive?"

"Which products are premium?"

Metric:

unit_cost

Scope:

product

Lower cost:

ascending

Higher cost:

descending


=========================================================
PRODUCT -> SUPPLIER
=========================================================

If the user asks which suppliers provide products, use:

domain:

supplier

operation:

lookup

metric:

product_supplier

entity:

product

If this requirement refers to products returned by an
earlier requirement, set depends_on to that requirement index.


=========================================================
SUPPLIER -> PRODUCT
=========================================================

If the user asks which products are supplied by suppliers,
use:

domain:

product

operation:

lookup

metric:

supplier_product

entity:

supplier

If the suppliers come from an earlier requirement,
set depends_on to that requirement index.


=========================================================
PRODUCT -> DEMAND
=========================================================

If the user asks for demand of products identified earlier:

domain:

demand

operation:

lookup

metric:

product_demand

entity:

product

depends_on:

index of the requirement producing the products


=========================================================
PRODUCT -> INVENTORY
=========================================================

If the user asks for inventory of products identified earlier:

domain:

inventory

operation:

lookup

metric:

product_inventory

entity:

product

depends_on:

index of the requirement producing the products


=========================================================
PRODUCT -> ORDERS
=========================================================

If the user asks how many historical orders exist for products:

domain:

order

operation:

lookup

metric:

total_orders

entity:

product

depends_on:

index of the requirement producing the products


=========================================================
PRODUCT -> DELIVERY
=========================================================

If the user asks about delivery performance for products:

domain:

delivery

operation:

lookup

metric:

product_delivery

entity:

product

depends_on:

index of the requirement producing the products


=========================================================
MULTI-REQUIREMENT EXAMPLE
=========================================================

User:

"Which products are expensive, what is their demand,
who supplies them, what is their inventory, and how many
orders did we have?"

Return:

{
    "intent": "multi_requirement",
    "metric": "unit_cost",
    "scope": "product",
    "complexity": "complex",
    "requires_entity": false,
    "confidence": 0.95,
    "requirements": [
        {
            "domain": "product",
            "operation": "rank",
            "metric": "unit_cost",
            "direction": "descending",
            "entity": "product",
            "entity_id": null,
            "depends_on": null
        },
        {
            "domain": "demand",
            "operation": "lookup",
            "metric": "product_demand",
            "direction": "none",
            "entity": "product",
            "entity_id": null,
            "depends_on": 0
        },
        {
            "domain": "supplier",
            "operation": "lookup",
            "metric": "product_supplier",
            "direction": "none",
            "entity": "product",
            "entity_id": null,
            "depends_on": 0
        },
        {
            "domain": "inventory",
            "operation": "lookup",
            "metric": "product_inventory",
            "direction": "none",
            "entity": "product",
            "entity_id": null,
            "depends_on": 0
        },
        {
            "domain": "order",
            "operation": "lookup",
            "metric": "total_orders",
            "direction": "none",
            "entity": "product",
            "entity_id": null,
            "depends_on": 0
        }
    ]
}


=========================================================
ANOTHER MULTI-REQUIREMENT EXAMPLE
=========================================================

User:

"Which suppliers have the highest delays, which products
do they supply, what is the demand for those products,
and how many orders did we receive?"

Return requirements equivalent to:

1. supplier / late_rate / rank
2. supplier_product / lookup / depends_on 0
3. product_demand / lookup / depends_on 1
4. total_orders / lookup / depends_on 1

=========================================================
DIRECTION
=========================================================

Use:

ascending

for:

- lowest
- least
- cheapest
- affordable
- lowest cost
- lowest demand

Use:

descending

for:

- highest
- most
- greatest
- top
- largest
- expensive
- highest cost
- highest demand
- highest risk

Use:

none

when ranking direction is not applicable.

=========================================================
ENTITY IDs
=========================================================

Recognize explicit IDs such as:

P00003
S014
R021

If the user explicitly provides an ID, preserve it.

=========================================================
IMPORTANT
=========================================================

Do NOT invent requirements that are not asked for.

Do NOT answer the question.

Do NOT calculate values.

Return ONLY valid JSON.

=========================================================
REQUIRED JSON FORMAT
=========================================================

{
    "intent": "one_supported_intent",
    "metric": "primary_metric_or_null",
    "scope": "primary_scope_or_null",
    "complexity": "simple_or_complex",
    "requires_entity": false,
    "confidence": 0.0,
    "requirements": [
        {
            "domain": "supported_domain",
            "operation": "supported_operation",
            "metric": "supported_metric",
            "direction": "ascending_or_descending_or_none",
            "entity": "entity_type_or_null",
            "entity_id": "explicit_id_or_null",
            "depends_on": null
        }
    ]
}

For a simple query, requirements should contain exactly
one requirement.

For a multi-requirement query, include every analytical
requirement.

Do not artificially limit the number of requirements.

confidence must be between 0.0 and 1.0.

Return no markdown.
Return no explanation.
Return only JSON.
"""

    # =========================================================
    # VALIDATE LLM RESULT
    # =========================================================

    def _validate_result(
        self,
        result: dict[str, Any],
    ) -> dict[str, Any] | None:

        if not isinstance(
            result,
            dict,
        ):
            return None

        intent = result.get(
            "intent"
        )

        if intent not in self.ALLOWED_INTENTS:
            return None

        metric = result.get(
            "metric"
        )

        if metric not in self.ALLOWED_METRICS:
            return None

        scope = result.get(
            "scope"
        )

        if scope not in self.ALLOWED_SCOPES:
            return None

        complexity = result.get(
            "complexity",
            "simple",
        )

        if complexity not in {
            "simple",
            "complex",
        }:
            complexity = "simple"

        confidence = self._safe_confidence(
            result.get(
                "confidence",
                0.0,
            )
        )

        requires_entity = bool(
            result.get(
                "requires_entity",
                False,
            )
        )

        # -----------------------------------------------------
        # Intent-specific metric normalization
        # -----------------------------------------------------

        expected_metric = {
            "sales_ranking": "total_sales",
            "demand_ranking": "total_demand",
            "stockout_ranking": "stockout_rate",
            "inventory_risk": "risk_score",
            "product_cost_ranking": "unit_cost",
            "order_analysis": "total_orders",
            "forecast": "forecast_demand",
            "anomaly_detection": "anomaly_score",
            "dashboard": "summary",
        }

        expected = expected_metric.get(
            intent
        )

        if expected is not None:
            metric = expected

        # -----------------------------------------------------
        # Scope normalization
        # -----------------------------------------------------

        if intent in {
            "sales_ranking",
            "demand_ranking",
            "stockout_ranking",
            "inventory_risk",
            "product_cost_ranking",
        }:

            scope = "product"

        elif intent == "supplier_risk":

            scope = "supplier"

        elif intent == "route_risk":

            scope = "route"

        elif intent == "forecast":

            if scope is None:
                scope = "forecast"

        elif intent == "dashboard":

            scope = "dashboard"

        elif intent == "complex_risk":

            scope = "supply_chain"
            complexity = "complex"

        # -----------------------------------------------------
        # Normalize requirements
        # -----------------------------------------------------

        raw_requirements = result.get(
            "requirements",
            []
        )

        requirements = self._validate_requirements(
            raw_requirements
        )

        # -----------------------------------------------------
        # Backward compatibility
        #
        # If the LLM returned a normal single intent but
        # forgot to provide requirements, construct the
        # primary requirement.
        # -----------------------------------------------------

        if not requirements and intent not in {
            "unknown",
            "ambiguous_product_ranking",
        }:

            primary_requirement = (
                self._build_requirement_from_classification(
                    intent=intent,
                    metric=metric,
                    scope=scope,
                    entity_type=result.get(
                        "entity_type"
                    ),
                    entity_id=result.get(
                        "entity_id"
                    ),
                )
            )

            if primary_requirement:
                requirements = [
                    primary_requirement
                ]

        # -----------------------------------------------------
        # Determine whether this is actually multi-step
        # -----------------------------------------------------

        if len(requirements) > 1:

            intent = "multi_requirement"
            complexity = "complex"

            # Primary metric/scope should come from
            # the first requirement.

            first = requirements[0]

            metric = first.get(
                "metric"
            )

            scope = first.get(
                "domain"
            )

        elif len(requirements) == 1:

            first = requirements[0]

            if intent == "multi_requirement":
                complexity = "complex"

            if metric is None:
                metric = first.get(
                    "metric"
                )

            if scope is None:
                scope = first.get(
                    "domain"
                )

        return {
            "intent": intent,
            "metric": metric,
            "scope": scope,
            "complexity": complexity,
            "requires_entity": requires_entity,
            "confidence": confidence,
            "requirements": requirements,
        }

    # =========================================================
    # VALIDATE REQUIREMENTS
    # =========================================================

    def _validate_requirements(
        self,
        raw_requirements: Any,
    ) -> list[dict[str, Any]]:

        if not isinstance(
            raw_requirements,
            list,
        ):
            return []

        validated: list[dict[str, Any]] = []

        for index, raw in enumerate(
            raw_requirements
        ):

            if not isinstance(
                raw,
                dict,
            ):
                continue

            domain = raw.get(
                "domain"
            )

            operation = raw.get(
                "operation",
                "lookup",
            )

            metric = raw.get(
                "metric"
            )

            direction = raw.get(
                "direction",
                "none",
            )

            entity = raw.get(
                "entity"
            )

            entity_id = raw.get(
                "entity_id"
            )

            depends_on = raw.get(
                "depends_on"
            )

            # -------------------------------------------------
            # Domain
            # -------------------------------------------------

            if domain not in self.ALLOWED_SCOPES:
                continue

            # -------------------------------------------------
            # Operation
            # -------------------------------------------------

            if operation not in self.ALLOWED_OPERATIONS:
                operation = "lookup"

            # -------------------------------------------------
            # Metric
            # -------------------------------------------------

            if metric not in self.ALLOWED_METRICS:
                continue

            # -------------------------------------------------
            # Direction
            # -------------------------------------------------

            if direction not in {
                "ascending",
                "descending",
                "none",
            }:

                direction = "none"

            # -------------------------------------------------
            # Entity
            # -------------------------------------------------

            if entity is not None:
                entity = str(
                    entity
                ).strip().lower()

            # -------------------------------------------------
            # Entity ID
            # -------------------------------------------------

            if entity_id is not None:
                entity_id = str(
                    entity_id
                ).strip().upper()

                if not entity_id:
                    entity_id = None

            # -------------------------------------------------
            # Dependency
            # -------------------------------------------------

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

                # A requirement cannot depend on itself
                # or on a future requirement.

                if (
                    depends_on is not None
                    and (
                        depends_on < 0
                        or depends_on >= index
                    )
                ):
                    depends_on = None

            validated.append(
                {
                    "domain": domain,
                    "operation": operation,
                    "metric": metric,
                    "direction": direction,
                    "entity": entity,
                    "entity_id": entity_id,
                    "depends_on": depends_on,
                }
            )

        return validated

    # =========================================================
    # BUILD SINGLE REQUIREMENT
    # =========================================================

    def _build_requirement_from_classification(
        self,
        intent: str,
        metric: str | None,
        scope: str | None,
        entity_type: str | None = None,
        entity_id: str | None = None,
    ) -> dict[str, Any] | None:

        if intent == "sales_ranking":

            return {
                "domain": "product",
                "operation": "rank",
                "metric": "total_sales",
                "direction": "descending",
                "entity": "product",
                "entity_id": entity_id,
                "depends_on": None,
            }

        if intent == "demand_ranking":

            return {
                "domain": "demand",
                "operation": "rank",
                "metric": "total_demand",
                "direction": "descending",
                "entity": "product",
                "entity_id": entity_id,
                "depends_on": None,
            }

        if intent == "stockout_ranking":

            return {
                "domain": "inventory",
                "operation": "rank",
                "metric": "stockout_rate",
                "direction": "descending",
                "entity": "product",
                "entity_id": entity_id,
                "depends_on": None,
            }

        if intent == "inventory_risk":

            return {
                "domain": "inventory",
                "operation": (
                    "explain"
                    if entity_id
                    else "rank"
                ),
                "metric": "risk_score",
                "direction": (
                    "none"
                    if entity_id
                    else "descending"
                ),
                "entity": "product",
                "entity_id": entity_id,
                "depends_on": None,
            }

        if intent == "supplier_risk":

            return {
                "domain": "supplier",
                "operation": "rank",
                "metric": "late_rate",
                "direction": "descending",
                "entity": "supplier",
                "entity_id": entity_id,
                "depends_on": None,
            }

        if intent == "delivery_risk":

            return {
                "domain": "delivery",
                "operation": "rank",
                "metric": "delivery_delay",
                "direction": "descending",
                "entity": "3pl",
                "entity_id": entity_id,
                "depends_on": None,
            }

        if intent == "route_risk":

            return {
                "domain": "route",
                "operation": "rank",
                "metric": "risk_score",
                "direction": "descending",
                "entity": "route",
                "entity_id": entity_id,
                "depends_on": None,
            }

        if intent == "forecast":

            return {
                "domain": "forecast",
                "operation": "forecast",
                "metric": "forecast_demand",
                "direction": "none",
                "entity": "product",
                "entity_id": entity_id,
                "depends_on": None,
            }

        if intent == "anomaly_detection":

            return {
                "domain": "order",
                "operation": "detect_anomaly",
                "metric": "anomaly_score",
                "direction": "descending",
                "entity": "order",
                "entity_id": entity_id,
                "depends_on": None,
            }

        if intent == "dashboard":

            return {
                "domain": "dashboard",
                "operation": "summarize",
                "metric": "summary",
                "direction": "none",
                "entity": "supply_chain",
                "entity_id": None,
                "depends_on": None,
            }

        if intent == "product_cost_ranking":

            return {
                "domain": "product",
                "operation": "rank",
                "metric": "unit_cost",
                "direction": "descending",
                "entity": "product",
                "entity_id": entity_id,
                "depends_on": None,
            }

        if intent == "complex_risk":

            return {
                "domain": "supply_chain",
                "operation": "impact_analysis",
                "metric": "summary",
                "direction": "none",
                "entity": entity_type or "supply_chain",
                "entity_id": entity_id,
                "depends_on": None,
            }

        return None

    # =========================================================
    # DETERMINISTIC FALLBACK
    # =========================================================

    def _deterministic_classification(
        self,
        query: str,
    ) -> dict[str, Any]:

        # -----------------------------------------------------
        # Detect multi-requirement query first
        # -----------------------------------------------------

        multi_requirements = (
            self._deterministic_multi_requirements(
                query
            )
        )

        if len(multi_requirements) > 1:

            first = multi_requirements[0]

            return {
                "intent": "multi_requirement",
                "metric": first.get(
                    "metric"
                ),
                "scope": first.get(
                    "domain"
                ),
                "complexity": "complex",
                "requires_entity": False,
                "confidence": 0.72,
                "requirements": multi_requirements,
            }

        # -----------------------------------------------------
        # Offers / bids / quotes
        # -----------------------------------------------------

        if self._contains_any(
            query,
            {"offer", "offers", "bid", "bids", "quote", "quotes"},
        ):
            is_supplier = self._contains_any(
                query,
                {"supplier", "suppliers", "vendor", "vendors"}
            ) or bool(re.search(r"\bS\d+\b", query.upper()))

            return {
                "intent": "offer_analysis",
                "metric": "supplier_offers",
                "scope": "offers",
                "complexity": "simple",
                "requires_entity": is_supplier,
                "entity_type": "supplier" if is_supplier else "product",
                "confidence": 0.85,
                "requirements": [
                    {
                        "domain": "offers",
                        "operation": "lookup",
                        "metric": "supplier_offers",
                        "direction": "none",
                        "entity": "supplier" if is_supplier else "product",
                        "entity_id": None,
                        "depends_on": None,
                    }
                ],
            }

        # -----------------------------------------------------
        # Unsupported / Out-of-domain queries
        # -----------------------------------------------------
        if self._contains_any(
            query,
            {"weather", "tokyo", "guitar", "strings in", "capital of", "president", "football", "cricket"}
        ):
            return {
                "intent": "unknown",
                "metric": None,
                "scope": None,
                "complexity": "simple",
                "requires_entity": False,
                "confidence": 0.0,
                "requirements": [],
                "method": "unsupported_domain",
            }

        # -----------------------------------------------------
        # Product impact from supplier disruptions
        # -----------------------------------------------------
        if (
            self._contains_any(query, {"disruption", "disruptions", "disrupted"})
            and self._contains_any(query, {"product", "products", "affected", "impact", "most affected", "vulnerable"})
        ):
            return {
                "intent": "product_disruption_impact",
                "metric": "supplier_disruption_impact",
                "scope": "product",
                "complexity": "simple",
                "requires_entity": False,
                "confidence": 0.92,
                "requirements": [
                    {
                        "domain": "product",
                        "operation": "rank",
                        "metric": "supplier_disruption_impact",
                        "direction": "descending",
                        "entity": "product",
                        "entity_id": None,
                        "depends_on": None,
                    }
                ],
            }

        # -----------------------------------------------------
        # Lead time anomaly / unusual lead time changes
        # -----------------------------------------------------
        if (
            self._contains_any(query, {"lead time", "lead times", "lead-time", "leadtime"})
            and self._contains_any(query, {"unusual", "change", "changes", "anomaly", "anomalies", "abnormal", "spike", "spikes", "identify"})
        ) or (
            self._contains_any(query, {"unusual changes", "lead time changes", "unusual lead times"})
        ):
            return {
                "intent": "lead_time_anomaly",
                "metric": "lead_time_anomaly",
                "scope": "supplier",
                "complexity": "simple",
                "requires_entity": False,
                "confidence": 0.92,
                "requirements": [
                    {
                        "domain": "supplier",
                        "operation": "detect_anomaly",
                        "metric": "lead_time_anomaly",
                        "direction": "descending",
                        "entity": "supplier",
                        "entity_id": None,
                        "depends_on": None,
                    }
                ],
            }

        # -----------------------------------------------------
        # Supplier investigation query
        # -----------------------------------------------------
        if (
            self._contains_any(query, {"investigate", "investigated", "investigation", "audit", "scrutiny", "look into"})
            and self._contains_any(query, {"supplier", "suppliers", "vendor", "vendors", "performance"})
        ):
            return {
                "intent": "supplier_investigation",
                "metric": "late_rate",
                "scope": "supplier",
                "complexity": "simple",
                "requires_entity": False,
                "confidence": 0.92,
                "requirements": [
                    {
                        "domain": "supplier",
                        "operation": "investigate",
                        "metric": "late_rate",
                        "direction": "descending",
                        "entity": "supplier",
                        "entity_id": None,
                        "depends_on": None,
                    }
                ],
            }

        # -----------------------------------------------------
        # Major supply chain risks
        # -----------------------------------------------------
        if (
            self._contains_any(query, {"major risk", "major risks", "major supply chain risks", "key risks", "top risks", "critical risks"})
            or (self._contains_any(query, {"risks"}) and self._contains_any(query, {"major", "biggest", "evidence supports", "supply chain risks"}))
        ):
            return {
                "intent": "major_risks",
                "metric": "major_risks",
                "scope": "dashboard",
                "complexity": "complex",
                "requires_entity": False,
                "confidence": 0.92,
                "requirements": [
                    {
                        "domain": "dashboard",
                        "operation": "explain",
                        "metric": "major_risks",
                        "direction": "none",
                        "entity": "supply_chain",
                        "entity_id": None,
                        "depends_on": None,
                    }
                ],
            }

        # -----------------------------------------------------
        # Supplier delivery delays / late risk
        # -----------------------------------------------------
        if (
            self._contains_any(query, {"supplier", "suppliers"})
            and self._contains_any(query, {"delivery delays", "delivery delay", "late delivery", "late deliveries", "delay risk", "delay risks", "high risk of delivery"})
        ):
            return {
                "intent": "supplier_delivery_risk",
                "metric": "late_rate",
                "scope": "supplier",
                "complexity": "simple",
                "requires_entity": False,
                "confidence": 0.92,
                "requirements": [
                    {
                        "domain": "supplier",
                        "operation": "rank",
                        "metric": "late_rate",
                        "direction": "descending",
                        "entity": "supplier",
                        "entity_id": None,
                        "depends_on": None,
                    }
                ],
            }

        # -----------------------------------------------------
        # Supplier delay affecting inventory
        # -----------------------------------------------------
        if (
            self._contains_any(query, {"supplier delay", "supplier delays", "delays from supplier"})
            and self._contains_any(query, {"inventory", "stockout", "availability", "stock"})
        ):
            return {
                "intent": "supplier_inventory_impact",
                "metric": "supplier_disruption_impact",
                "scope": "supply_chain",
                "complexity": "complex",
                "requires_entity": False,
                "confidence": 0.92,
                "requirements": [
                    {
                        "domain": "product",
                        "operation": "impact_analysis",
                        "metric": "supplier_disruption_impact",
                        "direction": "descending",
                        "entity": "supply_chain",
                        "entity_id": None,
                        "depends_on": None,
                    }
                ],
            }

        # -----------------------------------------------------
        # Semantic summary / overview / explain
        # -----------------------------------------------------

        if self._contains_any(
            query,
            {
                "summarize",
                "summary",
                "overview",
                "what should i know",
                "tell me about",
                "profile",
                "explain the relationship",
            },
        ):
            has_supplier = self._contains_any(
                query,
                {"supplier", "suppliers", "vendor", "vendors"},
            ) or bool(re.search(r"\bS\d+\b", query.upper()))

            has_product = self._contains_any(
                query,
                {"product", "products", "item", "sku"},
            ) or bool(re.search(r"\bP\d+\b", query.upper()))

            if has_supplier and not has_product:
                return {
                    "intent": "supplier_risk",
                    "metric": "late_rate",
                    "scope": "supplier",
                    "complexity": "simple",
                    "requires_entity": True,
                    "entity_type": "supplier",
                    "confidence": 0.88,
                    "requirements": [
                        {
                            "domain": "supplier",
                            "operation": "summarize",
                            "metric": "late_rate",
                            "direction": "descending",
                            "entity": "supplier",
                            "entity_id": None,
                            "depends_on": None,
                        }
                    ],
                }

            if has_product and not has_supplier:
                return {
                    "intent": "inventory_risk",
                    "metric": "risk_score",
                    "scope": "product",
                    "complexity": "simple",
                    "requires_entity": True,
                    "entity_type": "product",
                    "confidence": 0.88,
                    "requirements": [
                        {
                            "domain": "inventory",
                            "operation": "summarize",
                            "metric": "risk_score",
                            "direction": "none",
                            "entity": "product",
                            "entity_id": None,
                            "depends_on": None,
                        }
                    ],
                }

            return {
                "intent": "complex_risk",
                "metric": "summary",
                "scope": "supply_chain",
                "complexity": "complex",
                "requires_entity": False,
                "confidence": 0.82,
                "requirements": [
                    {
                        "domain": "supply_chain",
                        "operation": "explain",
                        "metric": "summary",
                        "direction": "none",
                        "entity": "supply_chain",
                        "entity_id": None,
                        "depends_on": None,
                    }
                ],
            }

        # -----------------------------------------------------
        # Product cost
        # -----------------------------------------------------

        if self._looks_like_cost_query(
            query
        ):

            direction = self._cost_direction(
                query
            )

            return {
                "intent": "product_cost_ranking",
                "metric": "unit_cost",
                "scope": "product",
                "complexity": "simple",
                "requires_entity": False,
                "confidence": 0.78,
                "requirements": [
                    {
                        "domain": "product",
                        "operation": "rank",
                        "metric": "unit_cost",
                        "direction": direction,
                        "entity": "product",
                        "entity_id": None,
                        "depends_on": None,
                    }
                ],
            }

        # -----------------------------------------------------
        # Sales
        # -----------------------------------------------------

        if (
            self._contains_any(
                query,
                {
                    "sales",
                    "revenue",
                    "selling",
                    "sells",
                    "sold",
                    "turnover",
                },
            )
            and self._contains_any(
                query,
                {
                    "most",
                    "highest",
                    "top",
                    "best",
                    "least",
                    "lowest",
                    "bottom",
                },
            )
        ):

            return {
                "intent": "sales_ranking",
                "metric": "total_sales",
                "scope": "product",
                "complexity": "simple",
                "requires_entity": False,
                "confidence": 0.80,
                "requirements": [
                    {
                        "domain": "product",
                        "operation": "rank",
                        "metric": "total_sales",
                        "direction": "descending",
                        "entity": "product",
                        "entity_id": None,
                        "depends_on": None,
                    }
                ],
            }

        # -----------------------------------------------------
        # Demand
        # -----------------------------------------------------

        if self._contains_any(
            query,
            {
                "demand",
                "in demand",
                "needed",
                "customer demand",
                "customers need",
                "customer needs",
            },
        ):

            return {
                "intent": "demand_ranking",
                "metric": "total_demand",
                "scope": "product",
                "complexity": "simple",
                "requires_entity": False,
                "confidence": 0.80,
                "requirements": [
                    {
                        "domain": "demand",
                        "operation": "rank",
                        "metric": "total_demand",
                        "direction": "descending",
                        "entity": "product",
                        "entity_id": None,
                        "depends_on": None,
                    }
                ],
            }

        # -----------------------------------------------------
        # Stockout
        # -----------------------------------------------------

        if self._contains_any(
            query,
            {
                "stockout",
                "stock out",
                "out of stock",
                "running out",
                "runs out",
                "inventory availability",
            },
        ):

            return {
                "intent": "stockout_ranking",
                "metric": "stockout_rate",
                "scope": "product",
                "complexity": "simple",
                "requires_entity": False,
                "confidence": 0.80,
                "requirements": [
                    {
                        "domain": "inventory",
                        "operation": "rank",
                        "metric": "stockout_rate",
                        "direction": "descending",
                        "entity": "product",
                        "entity_id": None,
                        "depends_on": None,
                    }
                ],
            }

        # -----------------------------------------------------
        # Inventory risk
        # -----------------------------------------------------

        if self._contains_any(
            query,
            {
                "inventory risk",
                "inventory risks",
                "risky product",
                "riskiest product",
                "product risk",
                "risk score",
            },
        ):

            return {
                "intent": "inventory_risk",
                "metric": "risk_score",
                "scope": "product",
                "complexity": "simple",
                "requires_entity": False,
                "confidence": 0.80,
                "requirements": [
                    {
                        "domain": "inventory",
                        "operation": "rank",
                        "metric": "risk_score",
                        "direction": "descending",
                        "entity": "product",
                        "entity_id": None,
                        "depends_on": None,
                    }
                ],
            }

        # -----------------------------------------------------
        # Semantic Summaries / Overviews (Phase 5)
        # -----------------------------------------------------

        if self._contains_any(
            query,
            {
                "summarize",
                "summary",
                "what should i know",
                "overview",
                "tell me about",
                "profile",
            },
        ):
            has_supplier = bool(re.search(r"\bS\d+\b", query.upper())) or "supplier" in query.lower()
            has_product = bool(re.search(r"\bP\d+\b", query.upper())) or "product" in query.lower()
            if has_supplier:
                return {
                    "intent": "supplier_risk",
                    "metric": "summary",
                    "scope": "supplier",
                    "complexity": "simple",
                    "requires_entity": True,
                    "confidence": 0.85,
                    "requirements": [
                        {
                            "domain": "supplier",
                            "operation": "summarize",
                            "metric": "late_rate",
                            "direction": "none",
                            "entity": "supplier",
                            "entity_id": None,
                            "depends_on": None,
                        }
                    ],
                }
            elif has_product:
                return {
                    "intent": "inventory_risk",
                    "metric": "summary",
                    "scope": "product",
                    "complexity": "simple",
                    "requires_entity": True,
                    "confidence": 0.85,
                    "requirements": [
                        {
                            "domain": "inventory",
                            "operation": "summarize",
                            "metric": "risk_score",
                            "direction": "none",
                            "entity": "product",
                            "entity_id": None,
                            "depends_on": None,
                        }
                    ],
                }
            else:
                return {
                    "intent": "complex_risk",
                    "metric": "summary",
                    "scope": "supply_chain",
                    "complexity": "complex",
                    "requires_entity": False,
                    "confidence": 0.80,
                    "requirements": [
                        {
                            "domain": "supply_chain",
                            "operation": "impact_analysis",
                            "metric": "summary",
                            "direction": "none",
                            "entity": "supply_chain",
                            "entity_id": None,
                            "depends_on": None,
                        }
                    ],
                }

        # -----------------------------------------------------
        # Inventory Level / Units
        # -----------------------------------------------------

        if (
            self._contains_any(
                query,
                {
                    "inventory of",
                    "current inventory",
                    "inventory level",
                    "stock level",
                    "how much inventory",
                    "inventory units",
                },
            )
            or (
                "inventory" in query.lower()
                and bool(re.search(r"\bP\d+\b", query.upper()))
                and not self._contains_any(query, {"risk", "stockout", "cover"})
            )
        ):
            return {
                "intent": "inventory_units",
                "metric": "inventory_units",
                "scope": "product",
                "complexity": "simple",
                "requires_entity": bool(re.search(r"\bP\d+\b", query.upper())),
                "confidence": 0.82,
                "requirements": [
                    {
                        "domain": "inventory",
                        "operation": "lookup" if re.search(r"\bP\d+\b", query.upper()) else "rank",
                        "metric": "inventory_units",
                        "direction": "descending",
                        "entity": "product",
                        "entity_id": None,
                        "depends_on": None,
                    }
                ],
            }

        # -----------------------------------------------------
        # Product supplier lookup
        # -----------------------------------------------------

        if (
            self._contains_any(
                query,
                {
                    "who supplied",
                    "who supplies",
                    "what supplier supplied",
                    "what supplier supplies",
                    "which supplier supplied",
                    "which supplier supplies",
                    "which suppliers supplied",
                    "which suppliers supply",
                    "supplied by",
                    "supplied product",
                    "supplier for",
                    "suppliers for",
                    "supplier of",
                    "supplied",
                    "supplies",
                    "provides product",
                    "provide product",
                    "provided product",
                    "provided by",
                    "products does supplier",
                    "products supplied",
                },
            )
            and (
                self._contains_any(
                    query,
                    {
                        "product",
                        "products",
                        "item",
                        "items",
                    },
                )
                or bool(re.search(r"\bP\d+\b", query.upper()))
                or bool(re.search(r"\bS\d+\b", query.upper()))
            )
            and not self._contains_any(query, {"risk", "delay", "late", "anomaly", "disruption", "anomalies", "impact"})
        ):
            is_supplier_target = bool(re.search(r"\bS\d+\b", query.upper())) or "supplier" in query.lower()
            metric_name = "supplier_product" if is_supplier_target else "product_supplier"
            entity_type = "supplier" if is_supplier_target else "product"

            return {
                "intent": "supplier_relationship_analysis",
                "metric": metric_name,
                "scope": "supplier",
                "complexity": "simple",
                "requires_entity": True,
                "entity_type": entity_type,
                "confidence": 0.82,
                "requirements": [
                    {
                        "domain": "supplier",
                        "operation": "lookup",
                        "metric": metric_name,
                        "direction": "none",
                        "entity": entity_type,
                        "entity_id": None,
                        "depends_on": None,
                    }
                ],
            }

        # -----------------------------------------------------
        # Supplier total orders
        # -----------------------------------------------------

        if (
            (
                self._contains_any(
                    query,
                    {
                        "supplier",
                        "suppliers",
                        "vendor",
                        "vendors",
                    },
                )
                or bool(re.search(r"\bS\d+\b", query.upper()))
            )
            and self._contains_any(
                query,
                {
                    "total orders",
                    "orders from supplier",
                    "order count",
                    "how many orders",
                    "how many total orders",
                    "number of orders",
                },
            )
        ):

            return {
                "intent": "order_analysis",
                "metric": "total_orders",
                "scope": "order",
                "complexity": "simple",
                "requires_entity": True,
                "confidence": 0.84,
                "requirements": [
                    {
                        "domain": "order",
                        "operation": "lookup",
                        "metric": "total_orders",
                        "direction": "none",
                        "entity": "supplier",
                        "entity_id": None,
                        "depends_on": None,
                    }
                ],
            }

        # -----------------------------------------------------
        # Supplier risk
        # -----------------------------------------------------

        if (
            (
                self._contains_any(
                    query,
                    {
                        "supplier",
                        "suppliers",
                        "my performance",
                    },
                )
                or bool(re.search(r"\bS\d+\b", query.upper()))
            )
            and self._contains_any(
                query,
                {
                    "risk",
                    "delay",
                    "late",
                    "performance",
                    "reliability",
                },
            )
        ):

            return {
                "intent": "supplier_risk",
                "metric": "late_rate",
                "scope": "supplier",
                "complexity": "simple",
                "requires_entity": False,
                "confidence": 0.78,
                "requirements": [
                    {
                        "domain": "supplier",
                        "operation": "rank",
                        "metric": "late_rate",
                        "direction": "descending",
                        "entity": "supplier",
                        "entity_id": None,
                        "depends_on": None,
                    }
                ],
            }

        # -----------------------------------------------------
        # Delivery
        # -----------------------------------------------------

        if self._contains_any(
            query,
            {
                "delivery delay",
                "delivery delays",
                "late delivery",
                "late deliveries",
                "delivery performance",
                "delivery risk",
                "delivery risks",
            },
        ):

            return {
                "intent": "delivery_risk",
                "metric": "delivery_delay",
                "scope": "delivery",
                "complexity": "simple",
                "requires_entity": False,
                "confidence": 0.78,
                "requirements": [
                    {
                        "domain": "delivery",
                        "operation": "rank",
                        "metric": "delivery_delay",
                        "direction": "descending",
                        "entity": "3pl",
                        "entity_id": None,
                        "depends_on": None,
                    }
                ],
            }

        # -----------------------------------------------------
        # Forecast
        # -----------------------------------------------------

        if self._contains_any(
            query,
            {
                "forecast",
                "forecasting",
                "future demand",
                "predicted demand",
                "expected demand",
            },
        ):

            return {
                "intent": "forecast",
                "metric": "forecast_demand",
                "scope": "forecast",
                "complexity": "simple",
                "requires_entity": False,
                "confidence": 0.78,
                "requirements": [
                    {
                        "domain": "forecast",
                        "operation": "forecast",
                        "metric": "forecast_demand",
                        "direction": "none",
                        "entity": "product",
                        "entity_id": None,
                        "depends_on": None,
                    }
                ],
            }

        # -----------------------------------------------------
        # Anomaly
        # -----------------------------------------------------

        if self._contains_any(
            query,
            {
                "anomaly",
                "anomalies",
                "unusual",
                "abnormal",
                "unexpected",
            },
        ):

            return {
                "intent": "anomaly_detection",
                "metric": "anomaly_score",
                "scope": "order",
                "complexity": "simple",
                "requires_entity": False,
                "confidence": 0.75,
                "requirements": [
                    {
                        "domain": "order",
                        "operation": "detect_anomaly",
                        "metric": "anomaly_score",
                        "direction": "descending",
                        "entity": "order",
                        "entity_id": None,
                        "depends_on": None,
                    }
                ],
            }

        # -----------------------------------------------------
        # Dashboard
        # -----------------------------------------------------

        if self._contains_any(
            query,
            {
                "overview",
                "summary",
                "summarize",
                "major supply chain risks",
                "overall supply chain",
            },
        ):

            return {
                "intent": "dashboard",
                "metric": "summary",
                "scope": "dashboard",
                "complexity": "simple",
                "requires_entity": False,
                "confidence": 0.75,
                "requirements": [
                    {
                        "domain": "dashboard",
                        "operation": "summarize",
                        "metric": "summary",
                        "direction": "none",
                        "entity": "supply_chain",
                        "entity_id": None,
                        "depends_on": None,
                    }
                ],
            }

        # -----------------------------------------------------
        # Complex impact
        # -----------------------------------------------------

        if (
            self._contains_any(
                query,
                {
                    "affect",
                    "impact",
                    "cause",
                    "lead to",
                    "result in",
                },
            )
            and self._contains_any(
                query,
                {
                    "supplier",
                    "inventory",
                    "stockout",
                    "delivery",
                    "demand",
                },
            )
        ):

            return {
                "intent": "complex_risk",
                "metric": "summary",
                "scope": "supply_chain",
                "complexity": "complex",
                "requires_entity": False,
                "confidence": 0.72,
                "requirements": [
                    {
                        "domain": "supply_chain",
                        "operation": "impact_analysis",
                        "metric": "summary",
                        "direction": "none",
                        "entity": "supply_chain",
                        "entity_id": None,
                        "depends_on": None,
                    }
                ],
            }

        # -----------------------------------------------------
        # Unknown
        # -----------------------------------------------------

        return {
            "intent": "unknown",
            "metric": None,
            "scope": None,
            "complexity": "simple",
            "requires_entity": False,
            "confidence": 0.20,
            "requirements": [],
        }

    # =========================================================
    # DETERMINISTIC MULTI-REQUIREMENT FALLBACK
    # =========================================================

    def _deterministic_multi_requirements(
        self,
        query: str,
    ) -> list[dict[str, Any]]:

        requirements: list[dict[str, Any]] = []

        # -----------------------------------------------------
        # Primary analytical requirement
        # -----------------------------------------------------

        primary: dict[str, Any] | None = None

        if self._contains_any(
            query,
            {
                "which products do i supply",
                "products do i supply",
                "products i supply",
                "what products do i supply",
                "products that i supply",
            },
        ):
            primary = {
                "domain": "product",
                "operation": "lookup",
                "metric": "supplier_product",
                "direction": "none",
                "entity": "supplier",
                "entity_id": None,
                "depends_on": None,
            }

        elif self._looks_like_cost_query(query):

            primary = {
                "domain": "product",
                "operation": "rank",
                "metric": "unit_cost",
                "direction": self._cost_direction(
                    query
                ),
                "entity": "product",
                "entity_id": None,
                "depends_on": None,
            }

        elif self._contains_any(
            query,
            {
                "demand",
                "in demand",
                "customer demand",
            },
        ):

            primary = {
                "domain": "demand",
                "operation": "rank",
                "metric": "total_demand",
                "direction": self._ranking_direction(
                    query,
                    "descending",
                ),
                "entity": "product",
                "entity_id": None,
                "depends_on": None,
            }

        elif self._contains_any(
            query,
            {
                "sales",
                "revenue",
                "selling",
                "sold",
            },
        ):

            primary = {
                "domain": "product",
                "operation": "rank",
                "metric": "total_sales",
                "direction": self._ranking_direction(
                    query,
                    "descending",
                ),
                "entity": "product",
                "entity_id": None,
                "depends_on": None,
            }

        elif self._contains_any(
            query,
            {
                "stockout",
                "stock out",
                "out of stock",
            },
        ):

            primary = {
                "domain": "inventory",
                "operation": "rank",
                "metric": "stockout_rate",
                "direction": "descending",
                "entity": "product",
                "entity_id": None,
                "depends_on": None,
            }

        elif self._contains_any(
            query,
            {
                "supplier",
                "suppliers",
            },
        ) and self._contains_any(
            query,
            {
                "delay",
                "delays",
                "late",
                "risk",
                "reliability",
            },
        ):

            primary = {
                "domain": "supplier",
                "operation": "rank",
                "metric": "late_rate",
                "direction": "descending",
                "entity": "supplier",
                "entity_id": None,
                "depends_on": None,
            }

        elif self._contains_any(query, {"who supplied", "who supplies", "what supplier supplied", "which supplier supplied", "which supplier supplies", "supplied by"}) and self._contains_any(query, {"orders", "order count", "total orders"}):
            primary = {
                "domain": "supplier",
                "operation": "lookup",
                "metric": "product_supplier",
                "direction": "none",
                "entity": "product",
                "entity_id": None,
                "depends_on": None,
            }

        elif self._contains_any(query, {"products are supplied", "products supplied", "what products", "which products"}) and self._contains_any(query, {"inventory", "stock", "stockout", "status"}):
            primary = {
                "domain": "supplier",
                "operation": "lookup",
                "metric": "supplier_product",
                "direction": "none",
                "entity": "supplier",
                "entity_id": None,
                "depends_on": None,
            }

        # -----------------------------------------------------
        # If no primary requirement, return empty.
        # -----------------------------------------------------

        if primary is None:
            return []

        requirements.append(
            primary
        )

        primary_index = 0

        # -----------------------------------------------------
        # Product -> Supplier
        # -----------------------------------------------------

        supplier_lookup_hints = {
            "supplier",
            "suppliers",
            "vendor",
            "vendors",
            "supply",
            "supplies",
            "supplied",
            "provided",
            "provides",
            "who supplies",
            "supplied by",
            "provided by",
        }

        product_reference_hints = {
            "product",
            "products",
            "item",
            "items",
            "which product",
            "what product",
            "which products",
            "what products",
        }

        explicit_supplier_scope_hints = {
            "this supplier",
            "that supplier",
            "the supplier",
            "associated supplier",
            "supplier associated",
            "supplier linked",
            "linked supplier",
            "from him",
            "from her",
            "from this supplier",
            "from that supplier",
            "which supplier is associated",
            "which supplier is linked",
        }

        direct_supplier_lookup = self._contains_any(
            query,
            {
                "who supplied",
                "who supplies",
                "what supplier supplied",
                "what supplier supplies",
                "which supplier supplied",
                "which supplier supplies",
                "which suppliers supplied",
                "which suppliers supply",
                "supplied by",
                "supplied product",
                "supplier for",
                "suppliers for",
                "supplier of",
                "supplies",
                "supplied",
                "provides product",
                "provide product",
                "provided product",
                "provided by",
            },
        ) and self._contains_any(
            query,
            product_reference_hints,
        )

        supplier_relationship_index = None

        if direct_supplier_lookup or (
            self._contains_any(
                query,
                supplier_lookup_hints,
            ) and (
                self._contains_any(
                    query,
                    product_reference_hints,
                )
                or primary["domain"] in {"product", "demand", "inventory"}
            )
        ):

            if primary["domain"] in {"product", "demand", "inventory"}:

                supplier_relationship_index = len(requirements)
                requirements.append(
                    {
                        "domain": "supplier",
                        "operation": "lookup",
                        "metric": "product_supplier",
                        "direction": "none",
                        "entity": "product",
                        "entity_id": None,
                        "depends_on": primary_index,
                    }
                )

            elif primary["domain"] == "supplier":

                supplier_relationship_index = len(requirements)
                requirements.append(
                    {
                        "domain": "product",
                        "operation": "lookup",
                        "metric": "supplier_product",
                        "direction": "none",
                        "entity": "supplier",
                        "entity_id": None,
                        "depends_on": primary_index,
                    }
                )

        # -----------------------------------------------------
        # Product -> Demand
        # -----------------------------------------------------

        if (
            primary["domain"] in {"product", "supplier", "inventory"}
            and self._contains_any(
                query,
                {
                    "demand",
                    "demand for",
                    "customer demand",
                    "customers need",
                    "their demand",
                },
            )
        ):

            requirements.append(
                {
                    "domain": "demand",
                    "operation": "lookup",
                    "metric": "total_demand",
                    "direction": "none",
                    "entity": "product",
                    "entity_id": None,
                    "depends_on": primary_index,
                }
            )

        # -----------------------------------------------------
        # Product -> Inventory
        # -----------------------------------------------------

        if (
            primary["domain"] in {"product", "demand", "supplier"}
            and self._contains_any(
                query,
                {
                    "inventory",
                    "stock level",
                    "stock levels",
                    "available stock",
                    "availability",
                    "their inventory",
                },
            )
        ):

            requirements.append(
                {
                    "domain": "inventory",
                    "operation": "lookup",
                    "metric": "inventory_units",
                    "direction": "none",
                    "entity": "product",
                    "entity_id": None,
                    "depends_on": primary_index,
                }
            )

        # -----------------------------------------------------
        # Supplier -> Orders
        # -----------------------------------------------------

        explicit_supplier_order_scope = self._contains_any(
            query,
            {
                "this supplier",
                "that supplier",
                "the supplier",
                "associated supplier",
                "supplier associated",
                "from him",
                "from her",
                "from this supplier",
                "from that supplier",
                "which supplier is associated",
                "which supplier is linked",
            },
        )

        if (
            self._contains_any(
                query,
                {
                    "supplier",
                    "suppliers",
                    "vendor",
                    "vendors",
                    "supplied by",
                    "supplied",
                    "who supplied",
                    "who supplies",
                    "i supply",
                    "supply",
                },
            )
            and self._contains_any(
                query,
                {
                    "orders",
                    "order count",
                    "number of orders",
                    "total orders",
                    "how many orders",
                    "historical orders",
                    "previous orders",
                    "past orders",
                    "order volume",
                },
            )
        ):

            supplier_order_depends_on = (
                supplier_relationship_index
                if supplier_relationship_index is not None
                and explicit_supplier_order_scope
                else primary_index
            )

            requirements.append(
                {
                    "domain": "order",
                    "operation": "lookup",
                    "metric": "total_orders",
                    "direction": "none",
                    "entity": "supplier",
                    "entity_id": None,
                    "depends_on": supplier_order_depends_on,
                }
            )

        # -----------------------------------------------------
        # Demand / Product -> Orders
        # -----------------------------------------------------

        if (
            primary["domain"] in {"product", "demand", "inventory"}
            and self._contains_any(
                query,
                {
                    "orders",
                    "order count",
                    "number of orders",
                    "historical orders",
                    "previous orders",
                    "past orders",
                },
            )
            and not (
                explicit_supplier_order_scope
                and supplier_relationship_index is not None
            )
        ):

            requirements.append(
                {
                    "domain": "order",
                    "operation": "lookup",
                    "metric": "total_orders",
                    "direction": "none",
                    "entity": "product",
                    "entity_id": None,
                    "depends_on": primary_index,
                }
            )

        # -----------------------------------------------------
        # Product -> Orders
        # -----------------------------------------------------

        if (
            primary["domain"] == "product"
            and self._contains_any(
                query,
                {
                    "orders",
                    "order count",
                    "number of orders",
                    "historical orders",
                    "previous orders",
                    "past orders",
                },
            )
            and not (
                explicit_supplier_order_scope
                and supplier_relationship_index is not None
            )
        ):

            requirements.append(
                {
                    "domain": "order",
                    "operation": "lookup",
                    "metric": "total_orders",
                    "direction": "none",
                    "entity": "product",
                    "entity_id": None,
                    "depends_on": primary_index,
                }
            )

        # -----------------------------------------------------
        # Product -> Delivery
        # -----------------------------------------------------

        if (
            primary["domain"] == "product"
            and self._contains_any(
                query,
                {
                    "delivery",
                    "deliveries",
                    "delay",
                    "delays",
                    "lead time",
                    "lead times",
                },
            )
        ):

            requirements.append(
                {
                    "domain": "delivery",
                    "operation": "lookup",
                    "metric": "product_delivery",
                    "direction": "none",
                    "entity": "product",
                    "entity_id": None,
                    "depends_on": primary_index,
                }
            )

        return requirements

    # =========================================================
    # COST QUERY DETECTION
    # =========================================================

    @staticmethod
    def _looks_like_cost_query(
        query: str,
    ) -> bool:

        direct_cost_terms = {
            "cost",
            "costs",
            "price",
            "prices",
            "priced",
            "expensive",
            "cheap",
            "cheapest",
            "affordable",
            "inexpensive",
            "budget",
            "premium",
            "luxury",
            "costly",
        }

        if QueryClassifier._contains_any(
            query,
            direct_cost_terms,
        ):
            return True

        semantic_cost_patterns = [
            r"\bcost\s+more\b",
            r"\bcost\s+less\b",
            r"\bcost\s+much\b",
            r"\bcost\s+a\s+lot\b",
            r"\bcost\s+us\b",
            r"\bcost\s+you\b",
            r"\bwon'?t\s+cost\s+much\b",
            r"\bwouldn'?t\s+cost\s+much\b",
            r"\bdon'?t\s+cost\s+much\b",
            r"\bdoesn'?t\s+cost\s+much\b",
            r"\bwill\s+not\s+cost\s+much\b",
            r"\bdo\s+not\s+cost\s+much\b",
            r"\bnot\s+cost\s+much\b",
            r"\bnot\s+expensive\b",
            r"\bwon'?t\s+be\s+expensive\b",
            r"\bwill\s+not\s+be\s+expensive\b",
        ]

        return any(
            re.search(
                pattern,
                query,
            )
            for pattern in semantic_cost_patterns
        )

    # =========================================================
    # COST DIRECTION
    # =========================================================

    @staticmethod
    def _cost_direction(
        query: str,
    ) -> str:

        lower_cost = {
            "cheap",
            "cheapest",
            "affordable",
            "inexpensive",
            "budget",
            "low cost",
            "lowest cost",
            "lower cost",
            "least expensive",
            "less expensive",
            "cost less",
            "won't cost much",
            "will not cost much",
            "wouldn't cost much",
            "would not cost much",
            "don't cost much",
            "do not cost much",
            "doesn't cost much",
            "does not cost much",
            "not cost much",
            "not expensive",
            "lowest price",
            "least expensive price",
        }

        higher_cost = {
            "expensive",
            "most expensive",
            "highest cost",
            "high cost",
            "costly",
            "premium",
            "luxury",
            "high priced",
            "high-priced",
            "higher priced",
            "higher-priced",
            "cost more",
            "highest price",
            "top price",
            "most expensive price",
        }

        if QueryClassifier._contains_any(
            query,
            lower_cost,
        ):
            return "ascending"

        if QueryClassifier._contains_any(
            query,
            higher_cost,
        ):
            return "descending"

        if QueryClassifier._contains_any(
            query,
            {
                "top",
                "highest",
                "most expensive",
                "expensive",
                "premium",
            },
        ) and QueryClassifier._contains_any(
            query,
            {
                "price",
                "cost",
            },
        ):
            return "descending"

        if QueryClassifier._contains_any(
            query,
            {
                "lowest",
                "cheapest",
                "least expensive",
                "affordable",
            },
        ) and QueryClassifier._contains_any(
            query,
            {
                "price",
                "cost",
            },
        ):
            return "ascending"

        return "none"

    # =========================================================
    # RANKING DIRECTION
    # =========================================================

    @staticmethod
    def _ranking_direction(
        query: str,
        default: str = "descending",
    ) -> str:

        ascending = {
            "least",
            "lowest",
            "smallest",
            "minimum",
            "fewest",
            "bottom",
            "least demand",
            "lowest demand",
            "least sales",
            "lowest sales",
        }

        descending = {
            "most",
            "highest",
            "largest",
            "maximum",
            "greatest",
            "top",
            "best",
            "highest sales",
            "highest demand",
        }

        if QueryClassifier._contains_any(
            query,
            ascending,
        ):
            return "ascending"

        if QueryClassifier._contains_any(
            query,
            descending,
        ):
            return "descending"

        return default

    # =========================================================
    # AMBIGUOUS PRODUCT QUERY
    # =========================================================

    @staticmethod
    def _is_ambiguous_product_query(
        query: str,
    ) -> bool:

        ranking_words = {
            "top",
            "best",
            "leading",
        }

        product_context = {
            "product",
            "products",
            "item",
            "items",
        }

        has_ranking = QueryClassifier._contains_any(
            query,
            ranking_words,
        )

        has_product = QueryClassifier._contains_any(
            query,
            product_context,
        )

        if has_ranking and has_product:

            known_metric_terms = {
                "sales",
                "revenue",
                "demand",
                "risk",
                "stockout",
                "cost",
                "price",
                "expensive",
                "cheap",
            }

            if QueryClassifier._contains_any(
                query,
                known_metric_terms,
            ):
                return False

            return True

        return False

    # =========================================================
    # ENTITY EXTRACTION
    # =========================================================

    @staticmethod
    def _extract_entity(
        query: str,
    ) -> tuple[str | None, str | None]:

        product_match = re.search(
            r"\b(P\d{3,})\b",
            query,
            re.IGNORECASE,
        )

        if product_match:
            return (
                "product",
                product_match.group(1).upper(),
            )

        supplier_match = re.search(
            r"\b(S\d{3,})\b",
            query,
            re.IGNORECASE,
        )

        if supplier_match:
            return (
                "supplier",
                supplier_match.group(1).upper(),
            )

        route_match = re.search(
            r"\b(R\d{3,})\b",
            query,
            re.IGNORECASE,
        )

        if route_match:
            return (
                "route",
                route_match.group(1).upper(),
            )

        return None, None

    # =========================================================
    # JSON EXTRACTION
    # =========================================================

    @staticmethod
    def _extract_json(
        response: Any,
    ) -> dict[str, Any] | None:

        if response is None:
            return None

        if isinstance(
            response,
            dict,
        ):
            return response

        text = str(
            response
        ).strip()

        if not text:
            return None

        # -----------------------------------------------------
        # Direct JSON
        # -----------------------------------------------------

        try:

            parsed = json.loads(
                text
            )

            if isinstance(
                parsed,
                dict,
            ):
                return parsed

        except (
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ):
            pass

        # -----------------------------------------------------
        # Markdown JSON
        # -----------------------------------------------------

        fenced_match = re.search(
            r"```(?:json)?\s*(\{.*?\})\s*```",
            text,
            re.DOTALL | re.IGNORECASE,
        )

        if fenced_match:

            try:

                parsed = json.loads(
                    fenced_match.group(1)
                )

                if isinstance(
                    parsed,
                    dict,
                ):
                    return parsed

            except (
                json.JSONDecodeError,
                TypeError,
                ValueError,
            ):
                pass

        # -----------------------------------------------------
        # Embedded JSON object
        # -----------------------------------------------------

        object_match = re.search(
            r"\{.*\}",
            text,
            re.DOTALL,
        )

        if object_match:

            try:

                parsed = json.loads(
                    object_match.group(0)
                )

                if isinstance(
                    parsed,
                    dict,
                ):
                    return parsed

            except (
                json.JSONDecodeError,
                TypeError,
                ValueError,
            ):
                pass

        return None

    # =========================================================
    # NORMALIZATION
    # =========================================================

    @staticmethod
    def _normalize(
        query: str,
    ) -> str:

        query = query.lower().strip()

        query = re.sub(
            r"\s+",
            " ",
            query,
        )

        return query

    # =========================================================
    # HELPER
    # =========================================================

    @staticmethod
    def _contains_any(
        text: str,
        phrases: set[str],
    ) -> bool:

        return any(
            phrase in text
            for phrase in phrases
        )

    # =========================================================
    # CONFIDENCE
    # =========================================================

    @staticmethod
    def _safe_confidence(
        value: Any,
    ) -> float:

        try:

            confidence = float(
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
                confidence,
            ),
        )