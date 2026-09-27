from __future__ import annotations

from typing import Any

from app.analytics.delivery_risk import DeliveryRiskAnalyzer


class DeliveryAgent:

    def __init__(self, data_service):
        self.data_service = data_service
        self.analyzer = DeliveryRiskAnalyzer()

    def run(
        self,
        top_n: int = 10
    ) -> dict[str, Any]:

        datasets = self.data_service.load_data()["datasets"]

        orders = datasets["orders_extended"]

        result = self.analyzer.analyze(orders)

        if result.empty:
            return {
                "status": "no_data",
                "agent": "Delivery Risk Analysis Agent",
                "findings": [],
                "evidence": []
            }

        findings = result.head(top_n).to_dict(
            orient="records"
        )

        evidence = []

        for row in findings:
            evidence.append({
                "three_pl": row.get("three_pl"),
                "risk_score": row.get("risk_score"),
                "risk_level": row.get("risk_level"),
                "late_rate": row.get("late_rate"),
                "avg_delay_days": row.get("avg_delay_days"),
                "total_orders": row.get("total_orders"),
                "risk_reason": row.get("risk_reason")
            })

        return {
            "status": "success",
            "agent": "Delivery Risk Analysis Agent",
            "findings": findings,
            "evidence": evidence
        }
    