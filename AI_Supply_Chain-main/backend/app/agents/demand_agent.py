from __future__ import annotations

from typing import Any

from app.services.data_service import DataService
from app.analytics.demand_ranking import DemandRankingAnalyzer


class DemandAgent:

    def __init__(self):
        self.data_service = DataService()
        self.analyzer = DemandRankingAnalyzer()

    def run(self, top_n: int = 10) -> dict[str, Any]:

        datasets = self.data_service.load_data()["datasets"]

        demand = datasets["demand"]

        result = self.analyzer.analyze(
            demand,
            top_n=top_n
        )

        findings = result.to_dict(
            orient="records"
        )

        return {
            "status": "success",
            "intent": "demand_ranking",
            "findings": findings,
            "evidence": findings,
            "message": (
                "Product demand ranking calculated "
                "from demand_units."
            )
        }
    