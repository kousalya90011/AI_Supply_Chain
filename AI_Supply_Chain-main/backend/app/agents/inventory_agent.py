from __future__ import annotations

from typing import Any

from app.analytics.inventory_risk import InventoryRiskAnalyzer
from app.services.evidence_service import EvidenceService


class InventoryAgent:

    def __init__(self, data_service):

        self.data_service = data_service

        self.analyzer = InventoryRiskAnalyzer(
            data_service
        )

        self.evidence_service = EvidenceService()

    # =========================================================
    # MAIN AGENT
    # =========================================================

    def run(
        self,
        entity_id: str | None = None,
        top_n: int = 10
    ) -> dict[str, Any]:

        # -----------------------------------------------------
        # SPECIFIC PRODUCT
        # -----------------------------------------------------

        if entity_id:

            return self._specific_product(
                entity_id
            )

        # -----------------------------------------------------
        # AGGREGATE INVENTORY QUERY
        # -----------------------------------------------------

        return self._aggregate_inventory(
            top_n
        )

    # =========================================================
    # SPECIFIC PRODUCT
    # =========================================================

    def _specific_product(
        self,
        product_id: str
    ) -> dict[str, Any]:

        evidence_result = (
            self.evidence_service.inventory_evidence(
                product_id
            )
        )

        if evidence_result.get("status") != "success":

            return {
                "status": evidence_result.get(
                    "status",
                    "error"
                ),
                "agent": "Inventory Risk Analysis Agent",
                "entity_id": product_id,
                "findings": [],
                "evidence": [],
                "message": evidence_result.get(
                    "message",
                    "Inventory evidence unavailable."
                )
            }

        risk = evidence_result.get(
            "risk",
            {}
        )

        evidence = evidence_result.get(
            "evidence",
            {}
        )

        finding = {
            "product_id": product_id,

            "risk_score": risk.get(
                "risk_score"
            ),

            "risk_level": risk.get(
                "risk_level"
            ),

            "stockout_rate": risk.get(
                "stockout_rate"
            ),

            "days_of_cover": risk.get(
                "days_of_cover",
                evidence.get("days_of_cover")
            ),

            "demand_pressure": risk.get(
                "demand_pressure",
                evidence.get("demand_pressure")
            ),

            "average_inventory": evidence.get(
                "average_inventory"
            ),

            "minimum_inventory": evidence.get(
                "minimum_inventory"
            ),

            "zero_inventory_records": evidence.get(
                "zero_inventory_records"
            ),

            "average_daily_demand": evidence.get(
                "average_daily_demand"
            ),

            "total_demand": evidence.get(
                "total_demand"
            ),

            "risk_reason": risk.get(
                "risk_reason"
            )
        }

        return {
            "status": "success",

            "agent": (
                "Inventory Risk Analysis Agent"
            ),

            "entity_id": product_id,

            "findings": [
                finding
            ],

            "evidence": [
                finding
            ],

            "source": evidence_result.get(
                "source",
                {}
            )
        }

    # =========================================================
    # AGGREGATE INVENTORY
    # =========================================================

    def _aggregate_inventory(
        self,
        top_n: int
    ) -> dict[str, Any]:

        result = self.analyzer.analyze(
            top_n=top_n
        )

        if result.empty:

            return {
                "status": "no_data",
                "agent": (
                    "Inventory Risk Analysis Agent"
                ),
                "findings": [],
                "evidence": []
            }

        findings = result.to_dict(
            orient="records"
        )

        evidence = []

        for row in findings:

            evidence.append({
                "product_id": row.get(
                    "product_id"
                ),

                "risk_score": row.get(
                    "risk_score"
                ),

                "risk_level": row.get(
                    "risk_level"
                ),

                "stockout_rate": row.get(
                    "stockout_rate"
                ),

                "days_of_cover": row.get(
                    "days_of_cover"
                ),

                "demand_pressure": row.get(
                    "demand_pressure"
                ),

                "risk_reason": row.get(
                    "risk_reason"
                )
            })

        return {
            "status": "success",

            "agent": (
                "Inventory Risk Analysis Agent"
            ),

            "entity_id": None,

            "findings": findings,

            "evidence": evidence,

            "source": {
                "dataset": "inventory_daily",
                "analysis": "InventoryRiskAnalyzer"
            }
        }
    