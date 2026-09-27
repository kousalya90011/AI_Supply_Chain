from __future__ import annotations

import time
from typing import Any

from app.query.planner import SemanticQueryPlanner
from app.query.validator import QueryPlanValidator
from app.query.factory import create_analytics_registry
from app.query.executor import QueryExecutor


class HybridRAGService:
    """
    Hybrid retrieval orchestration for supply-chain analytics.

    The system combines:

    1. Semantic retrieval and query planning
       - interprets the user request in natural language.

    2. Structured analytics retrieval
       - resolves numeric and relational facts from the
         warehouse / operational datasets.

    3. Evidence-grounded answer synthesis
       - only produces insights supported by retrieved
         analytical evidence.

    This pattern keeps the LLM from processing raw operational
    data directly and ensures every final answer is backed by
    concrete evidence.
    """

    retrieval_mode = "hybrid"
    pipeline = [
        "semantic_planning",
        "structured_analytics",
        "evidence_grounding",
    ]

    def query(self, query: str) -> dict[str, Any]:
        raise NotImplementedError(
            "HybridRAGService.query() must be implemented by a concrete service."
        )


class QueryService(HybridRAGService):
    """
    Main orchestration service for natural-language
    supply-chain queries.

    Architecture:

        User Query
            ↓
        Semantic Query Planner
            ↓
        Query Plan
            ↓
        Query Plan Validator
            ↓
        Multiple Query Requirements
            ↓
        Analytics Registry
            ↓
        Dependency-aware Executor
            ↓
        Combined Evidence
            ↓
        Human-readable Response

    Important:

    QueryService does NOT perform semantic classification.

    Semantic understanding is handled by QueryClassifier
    through SemanticQueryPlanner.

    QueryService coordinates execution and presentation.
    """

    def __init__(self) -> None:
        super().__init__()

        # -----------------------------------------------------
        # Semantic planning
        # -----------------------------------------------------

        self.planner = SemanticQueryPlanner()

        # -----------------------------------------------------
        # Validation
        # -----------------------------------------------------

        self.validator = QueryPlanValidator()

        # -----------------------------------------------------
        # Deterministic analytics
        # -----------------------------------------------------

        self.registry = create_analytics_registry()

        # -----------------------------------------------------
        # Requirement executor
        # -----------------------------------------------------

        self.executor = QueryExecutor(
            self.registry
        )

    # =========================================================
    # MAIN QUERY
    # =========================================================

    def query(
        self,
        query: str,
    ) -> dict[str, Any]:

        start_time = time.perf_counter()

        # -----------------------------------------------------
        # Empty query
        # -----------------------------------------------------

        if not query or not query.strip():

            return self._fallback_response(
                query=query,
                start_time=start_time,
                reason="empty_query",
            )

        cleaned_query = query.strip()

        try:

            # -------------------------------------------------
            # 1. Semantic planning
            # -------------------------------------------------

            plan = self.planner.plan(
                cleaned_query
            )

            # -------------------------------------------------
            # 2. Validate plan
            # -------------------------------------------------

            plan = self.validator.validate(
                plan
            )

            # -------------------------------------------------
            # 3. Execute requirements
            # -------------------------------------------------

            result = self.executor.execute(
                plan
            )

            # -------------------------------------------------
            # 4. Build final response
            # -------------------------------------------------

            return self._build_response(
                result=result,
                query=cleaned_query,
                start_time=start_time,
            )

        except Exception as exc:

            return self._fallback_response(
                query=cleaned_query,
                start_time=start_time,
                reason=str(exc),
            )

    # =========================================================
    # BUILD RESPONSE
    # =========================================================

    def _build_response(
        self,
        *,
        result: dict[str, Any],
        query: str,
        start_time: float,
    ) -> dict[str, Any]:

        status = result.get(
            "status",
            "success",
        )

        findings = result.get(
            "findings",
            [],
        )

        evidence = result.get(
            "evidence",
            [],
        )

        combined_findings = result.get(
            "combined_findings",
            findings,
        )

        combined_evidence = result.get(
            "combined_evidence",
            evidence,
        )

        requirement_results = result.get(
            "requirement_results",
            [],
        )

        planner_confidence = float(
            result.get(
                "planner_confidence",
                0.0,
            )
        )

        # -----------------------------------------------------
        # Fallback
        # -----------------------------------------------------

        fallback_used = status in {
            "fallback",
            "error",
        }

        # -----------------------------------------------------
        # Human-readable answer
        # -----------------------------------------------------

        answer = self._generate_answer(
            result=result,
            findings=findings,
            requirement_results=(
                requirement_results
            ),
            query=query,
        )

        # -----------------------------------------------------
        # Recommendations
        # -----------------------------------------------------

        recommendations = (
            self._generate_recommendations(
                result=result,
                findings=findings,
                requirement_results=(
                    requirement_results
                ),
            )
        )

        # -----------------------------------------------------
        # Entity information
        # -----------------------------------------------------

        entity_type = result.get(
            "entity"
        )

        entity_id = result.get(
            "entity_id"
        )

        # -----------------------------------------------------
        # Intent
        # -----------------------------------------------------

        intent = self._build_intent(
            result
        )

        # -----------------------------------------------------
        # Components
        # -----------------------------------------------------

        components_used = [
            "Semantic Query Planner",
            "Query Plan Validator",
            "Analytics Registry",
            "Dependency-aware Query Executor",
        ]

        if (
            len(requirement_results)
            > 1
        ):

            components_used.append(
                "Multi-Requirement Reasoning"
            )

        if fallback_used:

            components_used.append(
                "Fallback Engine"
            )

        # =====================================================
        # RESPONSE
        # =====================================================

        return {
            "status": (
                "success"
                if status == "success"
                else status
            ),

            "fallback_used": fallback_used,

            "confidence": planner_confidence,

            "answer": answer,

            # -------------------------------------------------
            # Evidence
            # -------------------------------------------------

            "evidence": combined_evidence,

            # -------------------------------------------------
            # Components
            # -------------------------------------------------

            "agents_used": components_used,

            # -------------------------------------------------
            # Intent
            # -------------------------------------------------

            "intent": intent,

            "entity_type": entity_type,

            "entity_id": entity_id,

            # -------------------------------------------------
            # Recommendations
            # -------------------------------------------------

            "recommendations": recommendations,

            # -------------------------------------------------
            # Primary query
            # -------------------------------------------------

            "metric": result.get(
                "metric"
            ),

            "operation": result.get(
                "operation"
            ),

            "domain": result.get(
                "domain"
            ),

            "direction": result.get(
                "direction"
            ),

            # -------------------------------------------------
            # Planner
            # -------------------------------------------------

            "planner_method": result.get(
                "planner_method"
            ),

            "planner_confidence": (
                planner_confidence
            ),

            # -------------------------------------------------
            # Primary findings
            # -------------------------------------------------

            "findings": findings,

            # -------------------------------------------------
            # Multi-requirement information
            # -------------------------------------------------

            "requirements": result.get(
                "requirements",
                [],
            ),

            "requirement_results": (
                requirement_results
            ),

            "requirement_count": result.get(
                "requirement_count",
                len(requirement_results),
            ),

            "successful_requirements": (
                result.get(
                    "successful_requirements",
                    0,
                )
            ),

            "failed_requirements": (
                result.get(
                    "failed_requirements",
                    0,
                )
            ),

            "combined_findings": (
                combined_findings
            ),

            "combined_evidence": (
                combined_evidence
            ),

            # -------------------------------------------------
            # Legacy compatibility
            # -------------------------------------------------

            "secondary_domain": result.get(
                "secondary_domain"
            ),

            "secondary_operation": result.get(
                "secondary_operation"
            ),

            "secondary_metric": result.get(
                "secondary_metric"
            ),

            "relationship": result.get(
                "relationship"
            ),

            "secondary_findings": result.get(
                "secondary_findings",
                [],
            ),

            "secondary_evidence": result.get(
                "secondary_evidence",
                [],
            ),

            # -------------------------------------------------
            # Timing
            # -------------------------------------------------

            "latency_ms": round(
                (
                    time.perf_counter()
                    - start_time
                )
                * 1000,
                2,
            ),

            "execution_latency_ms": result.get(
                "execution_latency_ms"
            ),

            "fallback_reason": (
                result.get(
                    "message"
                )
                if fallback_used
                else None
            ),
        }

    # =========================================================
    # ANSWER GENERATOR
    # =========================================================

    def _generate_answer(
        self,
        *,
        result: dict[str, Any],
        findings: list[Any],
        requirement_results: list[dict[str, Any]],
        query: str,
    ) -> str:

        status = result.get(
            "status"
        )

        # -----------------------------------------------------
        # Clarification
        # -----------------------------------------------------

        if status == "clarification_required":

            return result.get(
                "message",
                "Could you clarify your supply-chain question?",
            )

        # -----------------------------------------------------
        # Unsupported
        # -----------------------------------------------------

        if status == "unsupported":

            return result.get(
                "message",
                "This supply-chain analysis is not currently supported.",
            )

        # -----------------------------------------------------
        # Error
        # -----------------------------------------------------

        if status == "error":

            if requirement_results:

                successful = sum(
                    1
                    for item in requirement_results
                    if item.get("status")
                    == "success"
                )

                if successful > 0:

                    return (
                        "The analysis completed partially. "
                        f"{successful} requirement(s) were "
                        "successfully analyzed, while some "
                        "requirements could not be completed."
                    )

            return (
                "I could not complete the requested "
                "supply-chain analysis."
            )

        # -----------------------------------------------------
        # MULTI-REQUIREMENT QUERY
        # -----------------------------------------------------

        if len(requirement_results) > 1:

            return self._generate_multi_requirement_answer(
                requirement_results
            )

        # -----------------------------------------------------
        # Single requirement
        # -----------------------------------------------------

        return self._generate_single_requirement_answer(
            result=result,
            findings=findings,
        )

    # =========================================================
    # MULTI-REQUIREMENT ANSWER
    # =========================================================

    def _generate_multi_requirement_answer(
        self,
        requirement_results: list[dict[str, Any]],
    ) -> str:

        sections: list[str] = []

        for item in requirement_results:

            if item.get(
                "status"
            ) not in {
                "success",
                "completed",
            }:

                continue

            requirement = item.get(
                "requirement",
                {},
            )

            findings = item.get(
                "findings",
                [],
            )

            if not findings:

                continue

            metric = (
                requirement.get(
                    "metric"
                )
                if isinstance(
                    requirement,
                    dict,
                )
                else item.get(
                    "metric"
                )
            )

            domain = (
                requirement.get(
                    "domain"
                )
                if isinstance(
                    requirement,
                    dict,
                )
                else item.get(
                    "domain"
                )
            )

            direction = (
                requirement.get(
                    "direction",
                    "none",
                )
                if isinstance(
                    requirement,
                    dict,
                )
                else item.get(
                    "direction",
                    "none",
                )
            )

            summary = self._summarize_requirement(
                metric=metric,
                domain=domain,
                direction=direction,
                findings=findings,
            )

            if summary:

                sections.append(
                    summary
                )

        if not sections:

            return (
                "The requested multi-part supply-chain "
                "analysis completed, but no matching "
                "findings were returned."
            )

        return " ".join(
            sections
        )

    # =========================================================
    # REQUIREMENT SUMMARY
    # =========================================================

    def _summarize_requirement(
        self,
        *,
        metric: str | None,
        domain: str | None,
        direction: str,
        findings: list[Any],
    ) -> str:

        if not findings:

            return ""

        first = findings[0]

        if not isinstance(
            first,
            dict,
        ):

            return (
                f"The {domain or 'requested'} analysis "
                "returned supporting results."
            )

        ranking_word = self._ranking_word(
            direction
        )

        # -----------------------------------------------------
        # Cost
        # -----------------------------------------------------

        if metric == "unit_cost":

            product_id = first.get(
                "product_id",
                "the product",
            )

            cost = first.get(
                "unit_cost"
            )

            if cost is not None:

                return (
                    f"For product cost, {product_id} "
                    f"has the {ranking_word} unit cost "
                    f"at {float(cost):,.2f} per unit."
                )

        # -----------------------------------------------------
        # Sales
        # -----------------------------------------------------

        if metric == "total_sales":

            product_id = first.get(
                "product_id",
                "the product",
            )

            value = first.get(
                "total_sales"
            )

            if value is not None:

                return (
                    f"For sales, {product_id} has the "
                    f"{ranking_word} total sales at "
                    f"{float(value):,.2f}."
                )

        # -----------------------------------------------------
        # Demand
        # -----------------------------------------------------

        if metric == "total_demand":

            product_id = first.get(
                "product_id",
                "the product",
            )

            value = first.get(
                "total_demand"
            )

            if value is not None:

                return (
                    f"For demand, {product_id} has the "
                    f"{ranking_word} total demand at "
                    f"{float(value):,.2f} units."
                )

        # -----------------------------------------------------
        # Orders
        # -----------------------------------------------------

        if metric == "total_orders":

            product_id = first.get(
                "product_id"
            )

            supplier_id = first.get(
                "supplier_id"
            )

            total_orders = first.get(
                "total_orders"
            )

            entity_id = (
                product_id
                or supplier_id
                or "the selected entity"
            )

            if total_orders is not None:

                return (
                    f"{entity_id} has "
                    f"{int(total_orders):,} total orders "
                    "in the analyzed data."
                )

        # -----------------------------------------------------
        # Supplier mapping
        # -----------------------------------------------------

        if metric in {
            "product_supplier",
            "supplier_product",
        }:

            pairs: list[str] = []

            for finding in findings[:5]:

                if not isinstance(
                    finding,
                    dict,
                ):

                    continue

                product_id = finding.get(
                    "product_id"
                )

                supplier_id = finding.get(
                    "supplier_id"
                )

                supplier_name = finding.get(
                    "supplier_name"
                )

                if (
                    product_id
                    and supplier_id
                ):

                    label = (
                        f"{product_id} → "
                        f"{supplier_id}"
                    )

                    if supplier_name:

                        label += (
                            f" ({supplier_name})"
                        )

                    pairs.append(
                        label
                    )

            if pairs:

                return (
                    "Supplier relationships identified: "
                    + ", ".join(
                        pairs
                    )
                    + "."
                )

        # -----------------------------------------------------
        # Inventory
        # -----------------------------------------------------

        if metric == "inventory_units":

            product_id = first.get(
                "product_id",
                "the product",
            )

            inventory = first.get(
                "inventory_units"
            )

            if inventory is not None:

                return (
                    f"For inventory, {product_id} "
                    f"has {float(inventory):,.2f} units "
                    "in the selected result."
                )

        # -----------------------------------------------------
        # Stockout
        # -----------------------------------------------------

        if metric == "stockout_rate":

            product_id = first.get(
                "product_id",
                "the product",
            )

            rate = first.get(
                "stockout_rate"
            )

            if rate is not None:

                return (
                    f"{product_id} has the "
                    f"{ranking_word} stockout rate at "
                    f"{float(rate) * 100:.2f}%."
                )

        # -----------------------------------------------------
        # Risk
        # -----------------------------------------------------

        if metric == "risk_score":

            entity_id = (
                first.get("product_id")
                or first.get("supplier_id")
                or first.get("route_id")
                or "the selected entity"
            )

            score = first.get(
                "risk_score"
            )

            level = first.get(
                "risk_level"
            )

            if score is not None:

                answer = (
                    f"{entity_id} has the "
                    f"{ranking_word} risk score at "
                    f"{float(score):.2f}"
                )

                if level:

                    answer += (
                        f", classified as "
                        f"{level} risk."
                    )

                else:

                    answer += "."

                return answer

        # -----------------------------------------------------
        # Supplier late rate
        # -----------------------------------------------------

        if metric == "late_rate":

            supplier_id = first.get(
                "supplier_id",
                "the supplier",
            )

            rate = first.get(
                "late_rate"
            )

            if rate is not None:

                return (
                    f"{supplier_id} has the "
                    f"{ranking_word} late-order rate "
                    f"at {float(rate) * 100:.2f}%."
                )

        # -----------------------------------------------------
        # Delivery
        # -----------------------------------------------------

        if metric in {
            "delivery_delay",
            "delay_days",
        }:

            entity_id = (
                first.get("3pl")
                or first.get("supplier_id")
                or first.get("route_id")
                or "the delivery group"
            )

            delay = (
                first.get(
                    "avg_delay_days"
                )
                or first.get(
                    "delay_days"
                )
                or first.get(
                    "delivery_delay"
                )
            )

            if delay is not None:

                return (
                    f"{entity_id} has the "
                    f"{ranking_word} delivery delay "
                    f"at {float(delay):.2f} days."
                )

        # -----------------------------------------------------
        # Generic
        # -----------------------------------------------------

        return (
            f"The {domain or 'requested'} analysis "
            f"returned {len(findings)} finding(s) "
            f"for {metric or 'the requested metric'}."
        )

    # =========================================================
    # SINGLE REQUIREMENT ANSWER
    # =========================================================

    def _generate_single_requirement_answer(
        self,
        *,
        result: dict[str, Any],
        findings: list[Any],
    ) -> str:

        operation = result.get(
            "operation"
        )

        metric = result.get(
            "metric"
        )

        direction = result.get(
            "direction",
            "none",
        )

        # -----------------------------------------------------
        # No findings
        # -----------------------------------------------------

        if not findings:

            return (
                "The analysis completed successfully, "
                "but no matching supply-chain records "
                "were found."
            )

        # -----------------------------------------------------
        # Ranking / lookup summary
        # -----------------------------------------------------

        if operation in {"rank", "lookup"}:

            if metric == "total_orders" or metric in {
                "total_sales",
                "total_demand",
                "late_rate",
                "risk_score",
                "stockout_rate",
                "product_supplier",
                "supplier_product",
            }:

                return self._summarize_requirement(
                    metric=metric,
                    domain=result.get(
                        "domain"
                    ),
                    direction=direction,
                    findings=findings,
                )

            return self._summarize_requirement(
                metric=metric,
                domain=result.get(
                    "domain"
                ),
                direction=direction,
                findings=findings,
            )

        # -----------------------------------------------------
        # Explain
        # -----------------------------------------------------

        if operation == "explain":

            entity_id = result.get(
                "entity_id"
            )

            if entity_id:

                return (
                    f"The analysis found supporting "
                    f"evidence for {entity_id} based "
                    "on the requested supply-chain metric."
                )

            return (
                "The analysis found evidence explaining "
                "the requested supply-chain result."
            )

        # -----------------------------------------------------
        # Summarize
        # -----------------------------------------------------

        if operation == "summarize":

            return (
                f"The requested {metric or 'supply-chain'} "
                f"analysis completed using "
                f"{len(findings)} finding(s)."
            )

        # -----------------------------------------------------
        # Anomaly
        # -----------------------------------------------------

        if operation == "detect_anomaly":

            return (
                "The anomaly analysis completed using "
                f"{metric or 'the requested metric'}."
            )

        # -----------------------------------------------------
        # Forecast
        # -----------------------------------------------------

        if operation == "forecast":

            return (
                "The requested supply-chain forecast "
                "analysis was completed."
            )

        # -----------------------------------------------------
        # Impact
        # -----------------------------------------------------

        if operation == "impact_analysis":

            return (
                "The analysis identified the available "
                "evidence related to the requested "
                "supply-chain impact."
            )

        # -----------------------------------------------------
        # Investigation
        # -----------------------------------------------------

        if operation == "investigate":

            return (
                "The investigation identified "
                f"{len(findings)} supporting finding(s)."
            )

        return (
            "The supply-chain analysis completed successfully."
        )

    # =========================================================
    # RANKING WORD
    # =========================================================

    @staticmethod
    def _ranking_word(
        direction: str,
    ) -> str:

        if direction == "ascending":

            return "lowest"

        if direction == "descending":

            return "highest"

        return "requested"

    # =========================================================
    # RECOMMENDATIONS
    # =========================================================

    def _generate_recommendations(
        self,
        *,
        result: dict[str, Any],
        findings: list[Any],
        requirement_results: list[dict[str, Any]],
    ) -> list[str]:

        recommendations: list[str] = []

        # -----------------------------------------------------
        # Multi-requirement recommendations
        # -----------------------------------------------------

        if len(
            requirement_results
        ) > 1:

            metrics = []

            for item in requirement_results:

                requirement = item.get(
                    "requirement",
                    {},
                )

                if isinstance(
                    requirement,
                    dict,
                ):

                    metric = requirement.get(
                        "metric"
                    )

                    if metric:

                        metrics.append(
                            metric
                        )

            if (
                "risk_score" in metrics
                and "inventory_units" in metrics
            ):

                recommendations.append(
                    "Review inventory exposure together "
                    "with the identified risk drivers."
                )

            if (
                "total_demand" in metrics
                and "inventory_units" in metrics
            ):

                recommendations.append(
                    "Compare demand with available inventory "
                    "to identify products requiring closer "
                    "replenishment monitoring."
                )

            if (
                "product_supplier" in metrics
                and (
                    "late_rate" in metrics
                    or "delivery_delay" in metrics
                )
            ):

                recommendations.append(
                    "Review supplier and delivery performance "
                    "for products exposed to elevated "
                    "logistics risk."
                )

            if (
                "unit_cost" in metrics
                and "total_demand" in metrics
            ):

                recommendations.append(
                    "Compare product cost with demand before "
                    "making procurement or assortment decisions."
                )

        # -----------------------------------------------------
        # Single requirement recommendations
        # -----------------------------------------------------

        metric = result.get(
            "metric"
        )

        direction = result.get(
            "direction"
        )

        operation = result.get(
            "operation"
        )

        if findings:

            if metric == "risk_score":

                first = findings[0]

                risk_level = first.get(
                    "risk_level"
                )

                if risk_level in {
                    "CRITICAL",
                    "HIGH",
                }:

                    recommendations.append(
                        "Investigate the identified "
                        "high-risk product and review "
                        "its inventory and demand conditions."
                    )

            elif metric == "unit_cost":

                if direction == "ascending":

                    recommendations.append(
                        "Review low-cost products together "
                        "with their demand and sales performance "
                        "before making assortment decisions."
                    )

                else:

                    recommendations.append(
                        "Review high-cost products together "
                        "with their demand, sales, and inventory "
                        "exposure."
                    )

            elif metric == "stockout_rate":

                recommendations.append(
                    "Review replenishment planning for "
                    "products with elevated stockout rates."
                )

            elif metric == "late_rate":

                recommendations.append(
                    "Investigate suppliers with elevated "
                    "late-order rates and review their "
                    "recent delivery performance."
                )

            elif metric in {
                "delivery_delay",
                "delay_days",
            }:

                recommendations.append(
                    "Investigate delivery groups with "
                    "elevated delays and review their "
                    "recent operational performance."
                )

            elif metric == "total_demand":

                recommendations.append(
                    "Review inventory coverage for products "
                    "with consistently high demand."
                )

            elif metric == "total_sales":

                recommendations.append(
                    "Review inventory and supplier coverage "
                    "for high-sales products."
                )

        if operation == "explain":

            recommendations.append(
                "Review the supporting evidence before "
                "taking operational action."
            )

        # -----------------------------------------------------
        # Remove duplicates
        # -----------------------------------------------------

        unique: list[str] = []

        for recommendation in recommendations:

            if recommendation not in unique:

                unique.append(
                    recommendation
                )

        return unique

    # =========================================================
    # INTENT
    # =========================================================

    @staticmethod
    def _build_intent(
        result: dict[str, Any],
    ) -> str:

        domain = result.get(
            "domain"
        )

        operation = result.get(
            "operation"
        )

        metric = result.get(
            "metric"
        )

        if metric == "total_sales":

            return "sales_ranking"

        if metric == "unit_cost":

            return "product_cost_ranking"

        if metric == "total_demand":

            return "demand_ranking"

        if metric == "stockout_rate":

            return "stockout_ranking"

        if metric == "risk_score":

            return "inventory_risk"

        if metric == "late_rate":

            return "supplier_risk"

        if metric in {
            "delivery_delay",
            "delay_days",
        }:

            return "delivery_risk"

        if metric == "anomaly_score":

            return "anomaly_detection"

        if metric == "forecast_demand":

            return "forecast"

        if metric == "total_orders":

            return "order_analysis"

        if metric in {
            "product_supplier",
            "supplier_product",
        }:

            return "supplier_relationship_analysis"

        if domain:

            return domain

        return "unknown"

    # =========================================================
    # FALLBACK
    # =========================================================

    def _fallback_response(
        self,
        *,
        query: str,
        start_time: float,
        reason: str,
    ) -> dict[str, Any]:

        return {
            "status": "fallback",

            "fallback_used": True,

            "confidence": 0.0,

            "answer": (
                "I could not confidently process this "
                "supply-chain question. Please try "
                "asking about suppliers, products, "
                "inventory, demand, sales, delivery, "
                "forecasting, anomalies, or supply-chain risk."
            ),

            "evidence": [],

            "agents_used": [
                "Fallback Engine"
            ],

            "intent": "unknown",

            "entity_type": None,

            "entity_id": None,

            "recommendations": [],

            "metric": None,

            "operation": "clarify",

            "domain": None,

            "direction": "none",

            "planner_method": "fallback",

            "findings": [],

            "requirements": [],

            "requirement_results": [],

            "combined_findings": [],

            "combined_evidence": [],

            "requirement_count": 0,

            "successful_requirements": 0,

            "failed_requirements": 0,

            "planner_confidence": 0.0,

            "latency_ms": round(
                (
                    time.perf_counter()
                    - start_time
                )
                * 1000,
                2,
            ),

            "fallback_reason": reason,
        }