from __future__ import annotations

import time
from typing import Any

from app.services.data_service import DataService

from app.agents.router import QueryRouter
from app.agents.inventory_agent import InventoryAgent
from app.agents.supplier_agent import SupplierAgent
from app.agents.delivery_agent import DeliveryAgent
from app.agents.route_agent import RouteAgent
from app.agents.dashboard_agent import DashboardAgent
from app.agents.insight_agent import InsightAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.agents.forecast_agent import ForecastAgent
from app.agents.anomaly_agent import AnomalyAgent


class QueryService:

    def __init__(self):

        self.data_service = DataService()

        # ---------------------------------------------------------
        # ROUTER
        # ---------------------------------------------------------

        self.router = QueryRouter()

        # ---------------------------------------------------------
        # SPECIALIST AGENTS
        # ---------------------------------------------------------

        self.inventory_agent = InventoryAgent(
            self.data_service
        )

        self.supplier_agent = SupplierAgent(
            self.data_service
        )

        self.delivery_agent = DeliveryAgent(
            self.data_service
        )

        self.route_agent = RouteAgent(
            self.data_service
        )

        self.dashboard_agent = DashboardAgent(
            self.data_service
        )

        # ---------------------------------------------------------
        # INSIGHT + RECOMMENDATION
        # ---------------------------------------------------------

        self.insight_agent = InsightAgent()

        self.recommendation_agent = (
            RecommendationAgent()
        )

        self.forecast_agent = ForecastAgent(self.data_service)
        self.anomaly_agent = AnomalyAgent(self.data_service)
    # =============================================================
    # MAIN QUERY METHOD
    # =============================================================

    def query(
        self,
        query: str
    ) -> dict[str, Any]:

        start_time = time.perf_counter()

        # ---------------------------------------------------------
        # STEP 1 — ROUTING
        # ---------------------------------------------------------

        route = self.router.route(query)

        intent = route.get(
            "intent",
            "unknown"
        )

        entity_type = route.get(
            "entity_type"
        )

        entity_id = route.get(
            "entity_id"
        )

        requires_entity = route.get(
            "requires_entity",
            False
        )

        agents_used = [
            "Query Router"
        ]

        # ---------------------------------------------------------
        # STEP 2 — UNKNOWN QUERY
        # ---------------------------------------------------------

        if intent == "unknown":

            return self._fallback(
                query=query,
                intent=intent,
                agents_used=agents_used,
                start_time=start_time,
                reason="unsupported_query"
            )

        # ---------------------------------------------------------
        # STEP 3 — MISSING REQUIRED ENTITY
        # ---------------------------------------------------------

        if requires_entity and not entity_id:

            return self._fallback(
                query=query,
                intent=intent,
                agents_used=agents_used,
                start_time=start_time,
                reason="missing_entity"
            )

        try:

            # =====================================================
            # INVENTORY
            # =====================================================

            if intent == "inventory_risk":

                result = self.inventory_agent.run(
                    entity_id=entity_id,
                    top_n=10
                )

                agents_used.append(
                    "Inventory Risk Analysis Agent"
                )

            # =====================================================
            # SUPPLIER
            # =====================================================

            elif intent == "supplier_risk":

                result = self.supplier_agent.run(
                    entity_id=entity_id,
                    top_n=10
                )

                agents_used.append(
                    "Supplier Risk Analysis Agent"
                )

            # =====================================================
            # DELIVERY
            # =====================================================

            elif intent == "delivery_risk":

                result = self.delivery_agent.run(
                    top_n=10
                )

                agents_used.append(
                    "Delivery Risk Analysis Agent"
                )

            # =====================================================
            # ROUTE
            # =====================================================

            elif intent == "route_risk":

                result = self.route_agent.run(
                    entity_id=entity_id,
                    top_n=10
                )

                agents_used.append(
                    "Route Risk Analysis Agent"
                )

            # =====================================================
            # DASHBOARD
            # =====================================================

            elif intent == "dashboard":

                result = self.dashboard_agent.run()

                agents_used.append(
                    "Supply Chain Dashboard Agent"
                )

            # =====================================================
            # FORECAST
            # =====================================================

            elif intent == "forecast":
                result = self.forecast_agent.run(
                    product_id=entity_id,
                    horizon=7
                )
                agents_used.append(
                    "Demand Forecast Agent"
                )

            # =====================================================
            # ANOMALY
            # =====================================================

            elif intent == "anomaly_detection":
                result = self.anomaly_agent.run(
                    column="delay_days",
                    top_n=10
                )
                agents_used.append(
                    "Anomaly Detection Agent"
                )

            else:

                return self._fallback(
                    query=query,
                    intent=intent,
                    agents_used=agents_used,
                    start_time=start_time,
                    reason="unsupported_intent"
                )

            # =====================================================
            # STEP 4 — CHECK AGENT RESULT
            # =====================================================

            result_status = result.get(
                "status"
            )

            if result_status != "success":

                return self._fallback(
                    query=query,
                    intent=intent,
                    agents_used=agents_used,
                    start_time=start_time,
                    reason=result.get(
                        "message",
                        result_status or "agent_failure"
                    )
                )

            # =====================================================
            # STEP 5 — USE EVIDENCE DIRECTLY
            # =====================================================

            evidence = result.get(
                "evidence",
                []
            )

            findings = result.get(
                "findings",
                []
            )

            # Evidence can be a dictionary or list
            if evidence is None:
                evidence = []

            # If no evidence but findings exist,
            # use findings as evidence.
            if not evidence and findings:

                evidence = findings

            if not evidence:

                return self._fallback(
                    query=query,
                    intent=intent,
                    agents_used=agents_used,
                    start_time=start_time,
                    reason="invalid_evidence"
                )

            # =====================================================
            # STEP 6 — INSIGHT AGENT
            # =====================================================

            insight_input = {
                "findings": findings,
                "evidence": evidence
            }

            insight = self.insight_agent.run(
                intent=intent,
                evidence=insight_input
            )

            agents_used.append(
                "Supply Chain Insight Agent"
            )

            # =====================================================
            # STEP 7 — RECOMMENDATION AGENT
            # =====================================================

            recommendations = (
                self.recommendation_agent.run(
                    intent=intent,
                    evidence=insight_input
                )
            )

            agents_used.append(
                "Risk Recommendation Agent"
            )

            recommendation_list = (
                recommendations.get(
                    "recommendations",
                    []
                )
            )

            # =====================================================
            # STEP 8 — FINAL ANSWER
            # =====================================================

            answer = insight.get(
                "answer",
                "Supply-chain analysis completed."
            )

            if recommendation_list:

                answer += (
                    "\n\nRecommendations:\n"
                )

                for recommendation in (
                    recommendation_list
                ):

                    answer += (
                        f"- {recommendation}\n"
                    )

            confidence = float(
                insight.get(
                    "confidence",
                    0.70
                )
            )

            latency_ms = round(
                (
                    time.perf_counter()
                    - start_time
                ) * 1000,
                2
            )

            return {

                "status": "success",

                "fallback_used": False,

                "confidence": confidence,

                "answer": answer,

                "evidence": evidence,

                "agents_used": agents_used,

                "intent": intent,

                "entity_type": entity_type,

                "entity_id": entity_id,

                "recommendations": (
                    recommendation_list
                ),

                "latency_ms": latency_ms
            }

        # =========================================================
        # GLOBAL AGENT ERROR
        # =========================================================

        except Exception as exc:

            return self._fallback(
                query=query,
                intent=intent,
                agents_used=agents_used,
                start_time=start_time,
                reason=str(exc)
            )

    # =============================================================
    # FALLBACK ENGINE
    # =============================================================

    def _fallback(
        self,
        query: str,
        intent: str,
        agents_used: list[str],
        start_time: float,
        reason: str
    ) -> dict[str, Any]:

        latency_ms = round(
            (
                time.perf_counter()
                - start_time
            ) * 1000,
            2
        )

        if (
            "Fallback Engine"
            not in agents_used
        ):

            agents_used.append(
                "Fallback Engine"
            )

        # ---------------------------------------------------------
        # MISSING ENTITY
        # ---------------------------------------------------------

        if reason == "missing_entity":

            answer = (
                "This query requires a specific "
                "entity ID. Please provide a "
                "product, supplier, or route ID. "
                "For example: P00003."
            )

        # ---------------------------------------------------------
        # UNSUPPORTED QUERY
        # ---------------------------------------------------------

        elif reason == "unsupported_query":

            answer = (
                "I could not map this question to "
                "a supported supply-chain analysis. "
                "I can analyze supplier risk, "
                "delivery risk, inventory risk, "
                "route risk, demand forecasts, "
                "anomalies, and overall supply-chain "
                "metrics."
            )

        # ---------------------------------------------------------
        # INVALID EVIDENCE
        # ---------------------------------------------------------

        elif reason == "invalid_evidence":

            answer = (
                "The analysis did not produce "
                "sufficient evidence to provide "
                "a reliable answer."
            )

        # ---------------------------------------------------------
        # FORECAST NOT CONNECTED
        # ---------------------------------------------------------

        elif (
            reason
            == "forecast_agent_not_connected"
        ):

            answer = (
                "Demand forecasting is available "
                "through the forecast API, but the "
                "natural-language forecast agent "
                "has not yet been connected."
            )

        # ---------------------------------------------------------
        # ANOMALY NOT CONNECTED
        # ---------------------------------------------------------

        elif (
            reason
            == "anomaly_agent_not_connected"
        ):

            answer = (
                "Anomaly detection is available "
                "through the analytics API, but "
                "the natural-language anomaly agent "
                "has not yet been connected."
            )

        # ---------------------------------------------------------
        # GENERAL ERROR
        # ---------------------------------------------------------

        else:

            answer = (
                "The agent workflow encountered "
                "an issue. A deterministic fallback "
                "was used."
            )

        return {

            "status": "fallback",

            "fallback_used": True,

            "confidence": 0.30,

            "answer": answer,

            "evidence": [],

            "agents_used": agents_used,

            "intent": intent,

            "latency_ms": latency_ms,

            "fallback_reason": reason
        }