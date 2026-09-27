import pandas as pd

from app.analytics.risk_scoring import (
    RiskScoringEngine,
    calculate_risk_level
)



class SupplierRiskAnalyzer:

    def __init__(self):

        self.scorer = RiskScoringEngine()

    def analyze(
        self,
        orders: pd.DataFrame
    ) -> pd.DataFrame:

        required = {
            "supplier_id",
            "order_id",
            "units",
            "late_order"
        }

        missing = required - set(
            orders.columns
        )

        if missing:

            raise ValueError(
                f"Missing columns: {missing}"
            )

        supplier = (
            orders
            .groupby("supplier_id")
            .agg(
                total_orders=(
                    "order_id",
                    "count"
                ),
                total_units=(
                    "units",
                    "sum"
                ),
                late_orders=(
                    "late_order",
                    "sum"
                )
            )
            .reset_index()
        )

        supplier["late_rate"] = (
            supplier["late_orders"]
            / supplier["total_orders"]
        )

        total_units = supplier[
            "total_units"
        ].sum()

        supplier["volume_exposure"] = (
            supplier["total_units"]
            / total_units * 100
            if total_units > 0
            else 0
        )

        supplier["risk_score"] = supplier.apply(
            lambda row:
                self.scorer.calculate_supplier_score(
                    late_rate=row["late_rate"],
                    volume_exposure=row[
                        "volume_exposure"
                    ],
                    lead_time_risk=0
                ),
            axis=1
        )

        supplier["risk_level"] = (
            supplier["risk_score"]
            .apply(
                calculate_risk_level
            )
        )

        supplier["risk_reason"] = (
            "Late rate="
            + supplier["late_rate"]
            .round(3)
            .astype(str)
        )

        return supplier.sort_values(
            "risk_score",
            ascending=False
        )