import numpy as np
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

        max_units = supplier["total_units"].max()

        supplier["volume_exposure"] = (
            supplier["total_units"]
            / max_units * 100
            if max_units > 0
            else 0.0
        )

        extra_aggs = {}
        if "lead_time_days" in orders.columns:
            extra_aggs["avg_lead_time"] = ("lead_time_days", "mean")
            extra_aggs["std_lead_time"] = ("lead_time_days", "std")
        if "delay_days" in orders.columns:
            extra_aggs["avg_delay"] = ("delay_days", "mean")
        if "disruption_flag" in orders.columns:
            extra_aggs["disruption_rate"] = ("disruption_flag", "mean")

        if extra_aggs:
            extra_df = (
                orders
                .groupby("supplier_id")
                .agg(**extra_aggs)
                .reset_index()
            )
            supplier = supplier.merge(
                extra_df,
                on="supplier_id",
                how="left"
            )
            avg_delay = supplier.get(
                "avg_delay",
                pd.Series(0, index=supplier.index)
            ).fillna(0)
            std_lead = supplier.get(
                "std_lead_time",
                pd.Series(0, index=supplier.index)
            ).fillna(0)
            disr_rate = supplier.get(
                "disruption_rate",
                pd.Series(0, index=supplier.index)
            ).fillna(0)
            supplier["lead_time_risk"] = (
                (avg_delay * 6.0)
                + (std_lead * 3.5)
                + (disr_rate * 40.0)
            ).clip(0.0, 100.0)
        else:
            supplier["lead_time_risk"] = 0.0

        supplier["risk_score"] = supplier.apply(
            lambda row:
                self.scorer.calculate_supplier_score(
                    late_rate=row["late_rate"],
                    volume_exposure=row["volume_exposure"],
                    lead_time_risk=row["lead_time_risk"]
                ),
            axis=1
        )

        supplier["risk_level"] = (
            supplier["risk_score"]
            .apply(
                calculate_risk_level
            )
        )

        if "avg_delay" in supplier.columns:
            supplier["risk_reason"] = supplier.apply(
                lambda row: (
                    f"Late rate: {row['late_rate']:.1%}, "
                    f"Delay: {row['avg_delay']:.1f}d, "
                    f"Lead std: {row['std_lead_time']:.1f}d"
                ),
                axis=1
            )
        else:
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