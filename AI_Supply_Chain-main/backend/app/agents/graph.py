from __future__ import annotations

import time
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.state import SupplyChainState
from app.agents.router import QueryRouter

from app.agents.supplier_agent import SupplierAgent
from app.agents.inventory_agent import InventoryAgent
from app.agents.delivery_agent import DeliveryAgent
from app.agents.route_agent import RouteAgent
from app.agents.forecast_agent import ForecastAgent
from app.agents.anomaly_agent import AnomalyAgent

from app.agents.sales_agent import SalesAgent
from app.agents.demand_agent import DemandAgent
from app.agents.stockout_agent import StockoutAgent

from app.agents.complex_risk_agent import ComplexRiskAgent

from app.agents.insight_agent import InsightAgent
from app.agents.recommendation_agent import RecommendationAgent

from app.fallback.engine import FallbackEngine
from app.services.data_service import DataService


class SupplyChainGraph:

    def __init__(self):

        # =====================================================
        # SHARED DATA SERVICE
        # =====================================================

        self.data_service = DataService()

        # =====================================================
        # QUERY ROUTER
        # =====================================================

        self.router = QueryRouter()

        # =====================================================
        # SPECIALIST AGENTS
        # =====================================================

        self.supplier_agent = SupplierAgent(
            self.data_service
        )

        self.inventory_agent = InventoryAgent(
            self.data_service
        )

        self.delivery_agent = DeliveryAgent(
            self.data_service
        )

        self.route_agent = RouteAgent(
            self.data_service
        )

        self.forecast_agent = ForecastAgent(
            self.data_service
        )

        self.anomaly_agent = AnomalyAgent(
            self.data_service
        )

        # These agents manage their own DataService
        self.sales_agent = SalesAgent()
        self.demand_agent = DemandAgent()
        self.stockout_agent = StockoutAgent()

        # Complex multi-agent workflow
        self.complex_risk_agent = ComplexRiskAgent()

        # =====================================================
        # INSIGHT + RECOMMENDATION
        # =====================================================

        self.insight_agent = InsightAgent()

        self.recommendation_agent = RecommendationAgent()

        # =====================================================
        # FALLBACK
        # =====================================================

        self.fallback = FallbackEngine()

        # =====================================================
        # LANGGRAPH WORKFLOW
        # =====================================================

        workflow = StateGraph(SupplyChainState)

        workflow.add_node(
            "router",
            self.route_query
        )

        workflow.add_node(
            "specialist",
            self.run_specialist
        )

        workflow.add_node(
            "insight",
            self.generate_insight
        )

        workflow.add_node(
            "recommendation",
            self.generate_recommendation
        )

        workflow.add_node(
            "fallback",
            self.run_fallback
        )

        # -----------------------------------------------------
        # START
        # -----------------------------------------------------

        workflow.add_edge(
            START,
            "router"
        )

        # -----------------------------------------------------
        # ROUTER → SPECIALIST / FALLBACK
        # -----------------------------------------------------

        workflow.add_conditional_edges(
            "router",
            self.route_after_router,
            {
                "specialist": "specialist",
                "fallback": "fallback",
            },
        )

        # -----------------------------------------------------
        # SPECIALIST → INSIGHT
        # -----------------------------------------------------

        workflow.add_edge(
            "specialist",
            "insight"
        )

        # -----------------------------------------------------
        # INSIGHT → RECOMMENDATION
        # -----------------------------------------------------

        workflow.add_edge(
            "insight",
            "recommendation"
        )

        # -----------------------------------------------------
        # RECOMMENDATION → END
        # -----------------------------------------------------

        workflow.add_edge(
            "recommendation",
            END
        )

        # -----------------------------------------------------
        # FALLBACK → END
        # -----------------------------------------------------

        workflow.add_edge(
            "fallback",
            END
        )

        self.workflow = workflow.compile()

    # =========================================================
    # 1. QUERY ROUTING
    # =========================================================

    def route_query(
        self,
        state: SupplyChainState,
    ) -> dict[str, Any]:

        query = state.get(
            "query",
            ""
        ).strip()

        result = self.router.route(query)

        return {
            "intent": result.get(
                "intent",
                "unknown"
            ),

            "entity_type": result.get(
                "entity_type"
            ),

            "entity_id": result.get(
                "entity_id"
            ),

            "metric": result.get(
                "metric"
            ),

            "scope": result.get(
                "scope"
            ),

            "complexity": result.get(
                "complexity",
                "simple"
            ),

            "requires_entity": result.get(
                "requires_entity",
                False
            ),

            "confidence": result.get(
                "confidence",
                0.20
            ),
        }

    # =========================================================
    # 2. ROUTING DECISION
    # =========================================================

    def route_after_router(
        self,
        state: SupplyChainState,
    ) -> str:

        intent = state.get(
            "intent",
            "unknown"
        )

        if intent in {
            "unknown",
            "ambiguous_product_ranking",
        }:
            return "fallback"

        return "specialist"

    # =========================================================
    # 3. SPECIALIST AGENT EXECUTION
    # =========================================================

    def run_specialist(
        self,
        state: SupplyChainState,
    ) -> dict[str, Any]:

        intent = state.get(
            "intent",
            "unknown"
        )

        entity_id = state.get(
            "entity_id"
        )

        # =====================================================
        # SUPPLIER RISK
        # =====================================================

        if intent == "supplier_risk":

            result = self.supplier_agent.run(
                supplier_id=entity_id
            )

            return self._normalize_agent_result(
                result,
                "Supplier Risk Agent"
            )

        # =====================================================
        # INVENTORY RISK
        # =====================================================

        if intent == "inventory_risk":

            result = self.inventory_agent.run(
                product_id=entity_id
            )

            return self._normalize_agent_result(
                result,
                "Inventory Risk Agent"
            )

        # =====================================================
        # DELIVERY RISK
        # =====================================================

        if intent == "delivery_risk":

            result = self.delivery_agent.run()

            return self._normalize_agent_result(
                result,
                "Delivery Risk Agent"
            )

        # =====================================================
        # ROUTE RISK
        # =====================================================

        if intent == "route_risk":

            result = self.route_agent.run()

            return self._normalize_agent_result(
                result,
                "Route Risk Agent"
            )

        # =====================================================
        # FORECAST
        # =====================================================

        if intent == "forecast":

            result = self.forecast_agent.run(
                product_id=entity_id
            )

            return self._normalize_agent_result(
                result,
                "Forecast Agent"
            )

        # =====================================================
        # ANOMALY
        # =====================================================

        if intent == "anomaly_detection":

            result = self.anomaly_agent.run()

            return self._normalize_agent_result(
                result,
                "Anomaly Detection Agent"
            )

        # =====================================================
        # SALES RANKING
        # =====================================================

        if intent == "sales_ranking":

            result = self.sales_agent.run(
                top_n=10
            )

            return self._normalize_agent_result(
                result,
                "Sales Agent"
            )

        # =====================================================
        # DEMAND RANKING
        # =====================================================

        if intent == "demand_ranking":

            result = self.demand_agent.run(
                top_n=10
            )

            return self._normalize_agent_result(
                result,
                "Demand Agent"
            )

        # =====================================================
        # STOCKOUT RANKING
        # =====================================================

        if intent == "stockout_ranking":

            result = self.stockout_agent.run(
                top_n=10
            )

            return self._normalize_agent_result(
                result,
                "Stockout Agent"
            )

        # =====================================================
        # COMPLEX RISK
        # =====================================================

        if intent == "complex_risk":

            result = self.complex_risk_agent.run(
                supplier_id=entity_id
            )

            return self._normalize_agent_result(
                result,
                "Complex Risk Agent"
            )

        # =====================================================
        # DASHBOARD / SUPPLY CHAIN SUMMARY
        # =====================================================

        if intent == "dashboard":

            datasets = self.data_service.load_data()[
                "datasets"
            ]

            orders = datasets[
                "orders_extended"
            ]

            inventory = datasets[
                "inventory"
            ]

            total_orders = len(
                orders
            )

            late_orders = int(
                orders["late_order"].sum()
            )

            if total_orders > 0:

                late_rate = (
                    late_orders
                    / total_orders
                )

            else:

                late_rate = 0.0

            finding = {
                "total_orders": total_orders,

                "late_orders": late_orders,

                "late_rate": round(
                    late_rate,
                    4
                ),

                "inventory_records": len(
                    inventory
                ),
            }

            result = {
                "status": "success",

                "intent": "dashboard",

                "findings": [
                    finding
                ],

                "evidence": [
                    finding
                ],
            }

            return self._normalize_agent_result(
                result,
                "Supply Chain Insight Agent"
            )

        # =====================================================
        # UNKNOWN SPECIALIST
        # =====================================================

        return {
            "agent_result": {},

            "findings": [],

            "evidence": [],

            "agents_used": [],
        }

    # =========================================================
    # 4. LLM INSIGHT
    # =========================================================

    def generate_insight(
        self,
        state: SupplyChainState,
    ) -> dict[str, Any]:

        query = state.get(
            "query",
            ""
        )

        intent = state.get(
            "intent",
            "unknown"
        )

        evidence = state.get(
            "evidence",
            []
        )

        result = self.insight_agent.run(
            query=query,
            intent=intent,
            evidence=evidence,
        )

        return {
            "insight": result,

            "answer": result.get(
                "answer",
                "Supply-chain analysis completed."
            ),

            "confidence": result.get(
                "confidence",
                0.70
            ),
        }

    # =========================================================
    # 5. RECOMMENDATION AGENT
    # =========================================================

    def generate_recommendation(
        self,
        state: SupplyChainState,
    ) -> dict[str, Any]:

        intent = state.get(
            "intent",
            "unknown"
        )

        evidence = state.get(
            "evidence",
            []
        )

        result = self.recommendation_agent.run(
            intent=intent,
            evidence=evidence,
        )

        # -----------------------------------------------------
        # IMPORTANT:
        #
        # Existing RecommendationAgent returns a LIST.
        #
        # Example:
        #
        # [
        #     "Investigate top-selling products",
        #     "Monitor demand trends"
        # ]
        #
        # Therefore we must NOT blindly call result.get().
        # -----------------------------------------------------

        if isinstance(
            result,
            list
        ):

            recommendations = result

        elif isinstance(
            result,
            dict
        ):

            recommendations = result.get(
                "recommendations",
                []
            )

        else:

            recommendations = []

        # -----------------------------------------------------
        # Preserve existing agent trace
        # -----------------------------------------------------

        existing_agents = state.get(
            "agents_used",
            []
        )

        if not isinstance(
            existing_agents,
            list
        ):

            existing_agents = []

        agents_used = (
            existing_agents
            + ["Recommendation Agent"]
        )

        return {
            "recommendations": recommendations,

            "agents_used": agents_used,

            "status": "success",

            "fallback_used": state.get(
                "fallback_used",
                False
            ),
        }

    # =========================================================
    # 6. FALLBACK
    # =========================================================

    def run_fallback(
        self,
        state: SupplyChainState,
    ) -> dict[str, Any]:

        query = state.get(
            "query",
            ""
        )

        intent = state.get(
            "intent",
            "unknown"
        )

        if intent == "ambiguous_product_ranking":

            result = (
                self.fallback
                .ambiguous_product_ranking(
                    query
                )
            )

        else:

            result = (
                self.fallback
                .unsupported_query(
                    query
                )
            )

        return result

    # =========================================================
    # 7. NORMALIZE AGENT OUTPUT
    # =========================================================

    def _normalize_agent_result(
        self,
        result: dict[str, Any],
        agent_name: str,
    ) -> dict[str, Any]:

        # Safety check
        if not isinstance(
            result,
            dict
        ):

            return {
                "agent_result": {},

                "findings": [],

                "evidence": [],

                "agents_used": [
                    agent_name
                ],
            }

        findings = result.get(
            "findings",
            []
        )

        evidence = result.get(
            "evidence",
            findings
        )

        agents_used = result.get(
            "agents_used",
            [agent_name]
        )

        # Ensure lists
        if not isinstance(
            findings,
            list
        ):

            findings = []

        if not isinstance(
            evidence,
            list
        ):

            evidence = []

        if not isinstance(
            agents_used,
            list
        ):

            agents_used = [
                agent_name
            ]

        return {
            "agent_result": result,

            "findings": findings,

            "evidence": evidence,

            "agents_used": agents_used,
        }

    # =========================================================
    # 8. PUBLIC RUN METHOD
    # =========================================================

    def run(
        self,
        query: str,
    ) -> dict[str, Any]:

        start_time = time.perf_counter()

        initial_state: SupplyChainState = {

            "query": query,

            "agents_used": [],

            "fallback_used": False,

            "fallback_reason": None,
        }

        try:

            result = self.workflow.invoke(
                initial_state
            )

        except Exception as exc:

            latency_ms = round(
                (
                    time.perf_counter()
                    - start_time
                ) * 1000,
                2,
            )

            return {
                "status": "fallback",

                "fallback_used": True,

                "confidence": 0.20,

                "answer": (
                    "The supply-chain query "
                    "workflow encountered an "
                    "unexpected error. A "
                    "fallback response was used."
                ),

                "evidence": [],

                "findings": [],

                "agents_used": [
                    "LangGraph",
                    "Fallback Engine",
                ],

                "intent": "unknown",

                "entity_type": None,

                "entity_id": None,

                "recommendations": [],

                "latency_ms": latency_ms,

                "fallback_reason": str(
                    exc
                ),
            }

        # -----------------------------------------------------
        # LATENCY
        # -----------------------------------------------------

        latency_ms = round(
            (
                time.perf_counter()
                - start_time
            ) * 1000,
            2,
        )

        result["latency_ms"] = (
            latency_ms
        )

        # -----------------------------------------------------
        # DEFAULT STATUS
        # -----------------------------------------------------

        if "status" not in result:

            if result.get(
                "fallback_used",
                False
            ):

                result["status"] = (
                    "fallback"
                )

            else:

                result["status"] = (
                    "success"
                )

        # -----------------------------------------------------
        # DEFAULT FIELDS
        # -----------------------------------------------------

        if "fallback_used" not in result:

            result["fallback_used"] = (
                False
            )

        if "confidence" not in result:

            result["confidence"] = (
                0.70
            )

        if "recommendations" not in result:

            result["recommendations"] = []

        if "evidence" not in result:

            result["evidence"] = []

        if "findings" not in result:

            result["findings"] = []

        if "agents_used" not in result:

            result["agents_used"] = []

        return result
    