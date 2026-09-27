from __future__ import annotations

from typing import Any

from app.analytics.dashboard_metrics import DashboardMetrics


class DashboardAgent:

    def __init__(self, data_service):
        self.data_service = data_service
        self.dashboard = DashboardMetrics()

    def run(self) -> dict[str, Any]:

        datasets = self.data_service.load_data()["datasets"]

        metrics = self.dashboard.calculate(
            datasets["orders_extended"],
            datasets["inventory"]
        )

        return {
            "status": "success",
            "agent": "Supply Chain Dashboard Agent",
            "findings": [metrics],
            "evidence": [metrics]
        }