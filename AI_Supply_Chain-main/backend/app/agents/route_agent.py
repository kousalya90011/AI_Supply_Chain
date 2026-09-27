from __future__ import annotations

from typing import Any

from app.analytics.route_risk import RouteRiskAnalyzer


class RouteAgent:

    def __init__(self, data_service):
        self.data_service = data_service
        self.analyzer = RouteRiskAnalyzer()

    def run(
        self,
        entity_id: str | None = None,
        top_n: int = 10
    ) -> dict[str, Any]:

        datasets = self.data_service.load_data()["datasets"]

        orders = datasets["orders_extended"]

        result = self.analyzer.analyze(orders)

        if result.empty:
            return {
                "status": "no_data",
                "agent": "Route Risk Analysis Agent",
                "findings": [],
                "evidence": []
            }

        if entity_id:

            matching = result[
                result["route_id"].astype(str).str.upper()
                == entity_id.upper()
            ]

            if matching.empty:
                return {
                    "status": "not_found",
                    "agent": "Route Risk Analysis Agent",
                    "entity_id": entity_id,
                    "findings": [],
                    "evidence": []
                }

            row = matching.iloc[0].to_dict()

            return {
                "status": "success",
                "agent": "Route Risk Analysis Agent",
                "entity_id": entity_id,
                "findings": [row],
                "evidence": [self._evidence(row)]
            }

        findings = result.head(top_n).to_dict(
            orient="records"
        )

        return {
            "status": "success",
            "agent": "Route Risk Analysis Agent",
            "entity_id": None,
            "findings": findings,
            "evidence": [
                self._evidence(row)
                for row in findings
            ]
        }

    def _evidence(self, row: dict[str, Any]) -> dict[str, Any]:

        return {
            "route_id": row.get("route_id"),
            "risk_score": row.get("risk_score"),
            "risk_level": row.get("risk_level"),
            "late_rate": row.get("late_rate"),
            "total_orders": row.get("total_orders"),
            "late_orders": row.get("late_orders"),
            "risk_reason": row.get("risk_reason")
        }