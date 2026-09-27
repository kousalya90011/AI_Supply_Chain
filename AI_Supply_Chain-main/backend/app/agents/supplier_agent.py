from __future__ import annotations

from typing import Any

from app.analytics.supplier_risk import SupplierRiskAnalyzer
from app.services.evidence_service import EvidenceService


class SupplierAgent:

    def __init__(self, data_service):

        self.data_service = data_service

        self.analyzer = SupplierRiskAnalyzer()

        self.evidence_service = EvidenceService()

    # =========================================================
    # MAIN AGENT
    # =========================================================

    def run(
        self,
        entity_id: str | None = None,
        top_n: int = 10
    ) -> dict[str, Any]:

        if entity_id:

            return self._specific_supplier(
                entity_id
            )

        return self._aggregate_suppliers(
            top_n
        )

    # =========================================================
    # SPECIFIC SUPPLIER
    # =========================================================

    def _specific_supplier(
        self,
        supplier_id: str
    ) -> dict[str, Any]:

        evidence_result = (
            self.evidence_service.supplier_evidence(
                supplier_id
            )
        )

        if evidence_result.get("status") != "success":

            return {
                "status": evidence_result.get(
                    "status",
                    "error"
                ),

                "agent": (
                    "Supplier Risk Analysis Agent"
                ),

                "entity_id": supplier_id,

                "findings": [],

                "evidence": [],

                "message": evidence_result.get(
                    "message",
                    "Supplier evidence unavailable."
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
            "supplier_id": supplier_id,

            "risk_score": risk.get(
                "risk_score"
            ),

            "risk_level": risk.get(
                "risk_level"
            ),

            "late_rate": risk.get(
                "late_rate",
                evidence.get("late_rate")
            ),

            "total_orders": evidence.get(
                "total_orders"
            ),

            "late_orders": evidence.get(
                "late_orders"
            ),

            "total_units": evidence.get(
                "total_units"
            ),

            "risk_reason": risk.get(
                "risk_reason"
            )
        }

        return {
            "status": "success",

            "agent": (
                "Supplier Risk Analysis Agent"
            ),

            "entity_id": supplier_id,

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
    # AGGREGATE SUPPLIERS
    # =========================================================

    def _aggregate_suppliers(
        self,
        top_n: int
    ) -> dict[str, Any]:

        datasets = (
            self.data_service
            .load_data()
            ["datasets"]
        )

        orders = datasets[
            "orders_extended"
        ]

        result = self.analyzer.analyze(
            orders
        )

        if result.empty:

            return {
                "status": "no_data",
                "agent": (
                    "Supplier Risk Analysis Agent"
                ),
                "findings": [],
                "evidence": []
            }

        findings = (
            result
            .head(top_n)
            .to_dict(
                orient="records"
            )
        )

        evidence = []

        for row in findings:

            evidence.append({
                "supplier_id": row.get(
                    "supplier_id"
                ),

                "risk_score": row.get(
                    "risk_score"
                ),

                "risk_level": row.get(
                    "risk_level"
                ),

                "late_rate": row.get(
                    "late_rate"
                ),

                "total_orders": row.get(
                    "total_orders"
                ),

                "late_orders": row.get(
                    "late_orders"
                ),

                "total_units": row.get(
                    "total_units"
                ),

                "risk_reason": row.get(
                    "risk_reason"
                )
            })

        return {
            "status": "success",

            "agent": (
                "Supplier Risk Analysis Agent"
            ),

            "entity_id": None,

            "findings": findings,

            "evidence": evidence,

            "source": {
                "dataset": "orders_extended",
                "analysis": "SupplierRiskAnalyzer"
            }
        }