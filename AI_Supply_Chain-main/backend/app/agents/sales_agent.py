from __future__ import annotations

from typing import Any

from app.services.data_service import DataService
from app.analytics.product_sales import ProductSalesAnalyzer


class SalesAgent:

    def __init__(self):
        self.data_service = DataService()
        self.analyzer = ProductSalesAnalyzer()

    def run(
        self,
        top_n: int = 10
    ) -> dict[str, Any]:

        datasets = self.data_service.load_data()["datasets"]

        orders = datasets["orders_extended"]

        result = self.analyzer.analyze(
            orders,
            top_n=top_n
        )

        findings = result.to_dict(
            orient="records"
        )

        return {
            "status": "success",
            "intent": "sales_ranking",
            "findings": findings,
            "evidence": findings,
            "message": (
                "Product sales ranking calculated "
                "from order_value."
            )
        }
    