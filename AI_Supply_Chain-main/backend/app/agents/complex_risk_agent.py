from __future__ import annotations

from typing import Any

from app.services.data_service import DataService
from app.analytics.supplier_inventory_impact import (
    SupplierInventoryImpactAnalyzer
)


class ComplexRiskAgent:

    def __init__(self):

        self.data_service = DataService()

        self.analyzer = (
            SupplierInventoryImpactAnalyzer()
        )

    def run(
        self,
        supplier_id: str | None = None,
        top_n: int = 10
    ) -> dict[str, Any]:

        datasets = (
            self.data_service
            .load_data()["datasets"]
        )

        orders = datasets["orders_extended"]
        inventory = datasets["inventory"]

        # If no supplier ID is supplied, identify suppliers
        # with the highest late-order rate.

        if not supplier_id:

            supplier_summary = (
                orders
                .groupby("supplier_id")
                .agg(
                    total_orders=("order_id", "count"),
                    late_orders=("late_order", "sum")
                )
                .reset_index()
            )

            supplier_summary["late_rate"] = (
                supplier_summary["late_orders"]
                /
                supplier_summary["total_orders"]
            )

            supplier_summary = supplier_summary.sort_values(
                "late_rate",
                ascending=False
            )

            if supplier_summary.empty:

                return {
                    "status": "success",
                    "intent": "complex_risk",
                    "findings": [],
                    "evidence": [],
                    "agents_used": [
                        "Complex Risk Agent"
                    ]
                }

            # Investigate the highest-delay supplier.
            supplier_id = str(
                supplier_summary.iloc[0]["supplier_id"]
            )

        result = self.analyzer.analyze(
            orders=orders,
            inventory=inventory,
            supplier_id=supplier_id,
            top_n=top_n
        )

        evidence = result.get(
            "evidence",
            []
        )

        return {
            "status": "success",
            "intent": "complex_risk",
            "findings": result.get(
                "products",
                []
            ),
            "evidence": evidence,
            "supplier": result.get(
                "supplier"
            ),
            "agents_used": [
                "Supplier Risk Agent",
                "Delivery Risk Agent",
                "Inventory Risk Agent",
                "Complex Risk Agent"
            ],
            "message": (
                "Supplier delay impact was traced "
                "through affected products and inventory availability."
            )
        }
    