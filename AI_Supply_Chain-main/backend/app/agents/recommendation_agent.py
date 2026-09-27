from __future__ import annotations

from typing import Any


class RecommendationAgent:

    def run(
        self,
        intent: str,
        evidence: Any
    ) -> dict[str, Any]:

        # ---------------------------------------------------------
        # NORMALIZE EVIDENCE
        # ---------------------------------------------------------
        #
        # Existing graph may provide:
        #
        # {"findings": [...]}
        #
        # while some agents may provide:
        #
        # [...]
        #
        # Support both formats so the workflow remains compatible.
        # ---------------------------------------------------------

        if isinstance(evidence, dict):
            findings = evidence.get("findings", [])

        elif isinstance(evidence, list):
            findings = evidence

        else:
            findings = []

        if not findings:
            return {
                "recommendations": [],
                "status": "no_evidence"
            }

        first = findings[0]

        # =========================================================
        # ANOMALY DETECTION
        # =========================================================

        if intent == "anomaly_detection":

            anomaly_count = int(
                first.get("anomaly_count", 0)
            )

            if anomaly_count == 0:

                return {
                    "recommendations": [
                        "No statistical anomalies were detected in the analyzed records.",
                        "Continue monitoring delivery delays for emerging unusual patterns.",
                        "Review operational delay trends if the business experiences recurring late deliveries."
                    ],
                    "status": "success"
                }

            return {
                "recommendations": [
                    f"Investigate the {anomaly_count} identified anomalous records.",
                    "Check whether anomalies are associated with suppliers, routes, or logistics providers.",
                    "Review operational events around the identified anomalies.",
                    "Monitor recurring anomalies for systemic supply-chain issues."
                ],
                "status": "success"
            }

        # =========================================================
        # INVENTORY RISK
        # =========================================================

        if intent == "inventory_risk":

            days_of_cover = first.get("days_of_cover")

            recommendations = [
                "Review inventory coverage for the identified products.",
                "Compare current stock against recent demand.",
                "Investigate products with repeated stockout periods."
            ]

            if (
                days_of_cover is not None
                and float(days_of_cover) < 1
            ):
                recommendations.append(
                    "Consider replenishment before projected demand exceeds available stock."
                )

            return {
                "recommendations": recommendations,
                "status": "success"
            }

        if intent == "sales_ranking":

            return [
                "Review high-sales products for supplier and delivery dependencies.",
                "Prioritize continuity planning for products with high sales exposure."
            ]

        if intent == "demand_ranking":

            return [
                "Monitor highly demanded products for inventory availability.",
                "Compare demand with current inventory coverage."
            ]

        if intent == "stockout_ranking":

            return [
                "Investigate products with recurring stockouts.",
                "Compare stockout frequency with supplier delays and demand pressure."
            ]

        if intent == "complex_risk":

            return [
                "Investigate suppliers contributing to delayed orders.",
                "Prioritize affected products with high stockout rates.",
                "Review inventory coverage for products exposed to supplier delays.",
                "Consider supplier or logistics contingency plans for high-impact products."
            ]

        # =========================================================
        # SUPPLIER RISK
        # =========================================================

        if intent == "supplier_risk":

            risk_level = first.get(
                "risk_level",
                "UNKNOWN"
            )

            return {
                "recommendations": [
                    f"Review supplier performance for the {risk_level} risk suppliers.",
                    "Investigate recurring late deliveries and lead-time issues.",
                    "Monitor supplier performance trends over time."
                ],
                "status": "success"
            }

        # =========================================================
        # DELIVERY RISK
        # =========================================================

        if intent == "delivery_risk":

            return {
                "recommendations": [
                    "Review logistics providers with elevated delivery delays.",
                    "Investigate recurring late-shipment patterns.",
                    "Monitor delivery performance trends."
                ],
                "status": "success"
            }

        # =========================================================
        # ROUTE RISK
        # =========================================================

        if intent == "route_risk":

            return {
                "recommendations": [
                    "Review routes with elevated delay risk.",
                    "Investigate recurring transportation disruptions.",
                    "Monitor route performance over time."
                ],
                "status": "success"
            }

        # =========================================================
        # FORECAST
        # =========================================================

        if intent == "forecast":

            return {
                "recommendations": [
                    "Compare forecasted demand with current inventory.",
                    "Monitor demand trends for significant changes.",
                    "Review replenishment requirements based on forecasted demand."
                ],
                "status": "success"
            }

        # =========================================================
        # DASHBOARD
        # =========================================================

        if intent == "dashboard":

            return {
                "recommendations": [
                    "Prioritize investigation of the highest-risk supply-chain areas.",
                    "Monitor supplier, delivery, inventory and route risk trends.",
                    "Review changes in operational metrics over time."
                ],
                "status": "success"
            }

        if intent == "sales_ranking":
            return {
                "recommendations": [
                    "Review the highest-sales products for continued demand and revenue contribution.",
                    "Compare high-sales products against current inventory coverage.",
                    "Monitor supplier and delivery performance for high-value products.",
                    "Use sales concentration to prioritize supply continuity planning."
                ],
                "status": "success"
            }

        # =========================================================
        # DEFAULT
        # =========================================================

        return {
            "recommendations": [
                "Review the available supply-chain evidence.",
                "Monitor the relevant operational metrics."
            ],
            "status": "success"
        }
    