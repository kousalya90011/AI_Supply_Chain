from __future__ import annotations

from typing import Any

from app.llm.client import LLMClient
from app.llm.prompts import build_insight_prompt
from app.llm.structured_output import parse_llm_output


class InsightAgent:

    def __init__(self):

        self.llm = LLMClient()

    # =========================================================
    # MAIN METHOD
    # =========================================================

    def run(
        self,
        query: str,
        intent: str,
        evidence: list[dict[str, Any]]
    ) -> dict[str, Any]:

        # -----------------------------------------------------
        # BUILD LLM PROMPT
        # -----------------------------------------------------

        messages = build_insight_prompt(
            query=query,
            intent=intent,
            evidence=evidence
        )

        # -----------------------------------------------------
        # CALL LLM
        # -----------------------------------------------------

        try:

            response = self.llm.generate(
                messages=messages
            )

        except Exception as exc:

            return self._fallback_insight(
                intent=intent,
                evidence=evidence,
                reason=str(exc)
            )

        # -----------------------------------------------------
        # EXTRACT CONTENT
        # -----------------------------------------------------

        content = response.get(
            "content",
            ""
        )

        # -----------------------------------------------------
        # PARSE STRUCTURED OUTPUT
        # -----------------------------------------------------

        try:

            parsed = parse_llm_output(
                content
            )

        except Exception as exc:

            return self._fallback_insight(
                intent=intent,
                evidence=evidence,
                reason=str(exc)
            )

        # -----------------------------------------------------
        # BUILD FINAL INSIGHT
        # -----------------------------------------------------

        return {

            "status": "success",

            "answer": parsed.get(
                "summary",
                "Supply-chain analysis completed."
            ),

            "confidence": parsed.get(
                "confidence",
                0.70
            ),

            "key_findings": parsed.get(
                "key_findings",
                []
            ),

            "business_impact": parsed.get(
                "business_impact",
                ""
            ),

            "recommended_actions": parsed.get(
                "recommended_actions",
                []
            ),

            "provider": response.get(
                "provider"
            ),

            "model": response.get(
                "model"
            ),

            "fallback_used": response.get(
                "fallback_used",
                False
            )
        }

    # =========================================================
    # DETERMINISTIC FALLBACK
    # =========================================================

    def _fallback_insight(
        self,
        intent: str,
        evidence: list[dict[str, Any]],
        reason: str
    ) -> dict[str, Any]:

        if not evidence:

            return {

                "status": "fallback",

                "answer": (
                    "The analysis completed, "
                    "but sufficient evidence was "
                    "not available."
                ),

                "confidence": 0.30,

                "key_findings": [],

                "business_impact": "",

                "recommended_actions": [],

                "fallback_reason": reason
            }

        first = evidence[0]

        # -----------------------------------------------------
        # INVENTORY
        # -----------------------------------------------------

        if intent == "inventory_risk":

            product_id = first.get(
                "product_id",
                "the requested product"
            )

            risk_level = first.get(
                "risk_level",
                "UNKNOWN"
            )

            risk_score = first.get(
                "risk_score",
                "N/A"
            )

            stockout_rate = first.get(
                "stockout_rate"
            )

            days_of_cover = first.get(
                "days_of_cover"
            )

            answer = (
                f"Product {product_id} has "
                f"inventory risk level "
                f"{risk_level} with a "
                f"risk score of {risk_score}."
            )

            findings = [
                f"Stockout rate is {stockout_rate}.",
                f"Days of inventory cover is {days_of_cover}."
            ]

        # -----------------------------------------------------
        # FORECAST
        # -----------------------------------------------------

        elif intent == "forecast":

            product_id = first.get(
                "product_id",
                "the requested product"
            )

            average_demand = first.get(
                "average_recent_demand"
            )

            trend = first.get(
                "trend_per_day"
            )

            answer = (
                f"Demand forecasting was completed "
                f"for product {product_id}. "
                f"The recent average demand is "
                f"{average_demand} units per day."
            )

            findings = [
                f"Recent average demand: {average_demand}.",
                f"Demand trend per day: {trend}."
            ]

        # -----------------------------------------------------
        # ANOMALY
        # -----------------------------------------------------

        elif intent == "anomaly_detection":

            anomaly_count = first.get(
                "anomaly_count",
                0
            )

            total_records = first.get(
                "total_records",
                0
            )

            answer = (
                f"Anomaly detection identified "
                f"{anomaly_count} anomalies out of "
                f"{total_records} records."
            )

            findings = [
                f"Anomaly count: {anomaly_count}.",
                f"Total records analyzed: {total_records}."
            ]

        # -----------------------------------------------------
        # SUPPLIER
        # -----------------------------------------------------

        elif intent == "supplier_risk":

            supplier_id = first.get(
                "supplier_id",
                "the requested supplier"
            )

            risk_level = first.get(
                "risk_level",
                "UNKNOWN"
            )

            answer = (
                f"Supplier {supplier_id} has "
                f"a risk level of {risk_level}."
            )

            findings = [
                f"Supplier risk level: {risk_level}."
            ]

        # -----------------------------------------------------
        # ROUTE
        # -----------------------------------------------------

        elif intent == "route_risk":

            route_id = first.get(
                "route_id",
                "the requested route"
            )

            answer = (
                f"Route {route_id} was analyzed "
                "for delivery risk."
            )

            findings = [
                "Route risk analysis was completed "
                "using the available evidence."
            ]

        # -----------------------------------------------------
        # DELIVERY
        # -----------------------------------------------------

        elif intent == "delivery_risk":

            answer = (
                "Delivery risk analysis was "
                "completed using the available "
                "operational evidence."
            )

            findings = [
                "Delivery performance evidence "
                "was analyzed."
            ]

        # -----------------------------------------------------
        # DASHBOARD
        # -----------------------------------------------------

        elif intent == "dashboard":

            answer = (
                "The supply-chain dashboard "
                "analysis was completed."
            )

            findings = [
                "Overall supply-chain metrics "
                "were analyzed."
            ]

        # -----------------------------------------------------
        # GENERIC
        # -----------------------------------------------------

        else:

            answer = (
                "Supply-chain analysis completed "
                "using validated evidence."
            )

            findings = [
                "Validated supply-chain evidence "
                "was analyzed."
            ]

        return {

            "status": "fallback",

            "answer": answer,

            "confidence": 0.60,

            "key_findings": findings,

            "business_impact": (
                "Operational impact should be "
                "reviewed using the supplied "
                "evidence."
            ),

            "recommended_actions": [],

            "fallback_reason": reason
        }