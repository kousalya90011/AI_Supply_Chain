from __future__ import annotations

from typing import Any

from app.services.data_service import DataService
from app.analytics.stockout_ranking import StockoutRankingAnalyzer


class StockoutAgent:

    def __init__(self):
        self.data_service = DataService()
        self.analyzer = StockoutRankingAnalyzer()

    def run(self, top_n: int = 10) -> dict[str, Any]:

        datasets = self.data_service.load_data()["datasets"]

        inventory = datasets["inventory"]

        result = self.analyzer.analyze(
            inventory,
            top_n=top_n
        )

        findings = result.to_dict(
            orient="records"
        )

        return {
            "status": "success",
            "intent": "stockout_ranking",
            "findings": findings,
            "evidence": findings,
            "message": (
                "Product stockout ranking calculated "
                "from inventory history."
            )
        }
    