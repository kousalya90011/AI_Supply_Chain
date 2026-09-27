import pandas as pd

from app.analytics.risk_scoring import (
    RiskScoringEngine,
    calculate_risk_level
)

class DeliveryRiskAnalyzer:

    def __init__(self):
        self.scorer = RiskScoringEngine()

    def _find_column(
        self,
        df: pd.DataFrame,
        candidates: list[str]
    ) -> str | None:

        for column in candidates:
            if column in df.columns:
                return column

        return None

    def analyze(self, orders: pd.DataFrame) -> pd.DataFrame:

        three_pl_column = self._find_column(
            orders,
            [
                "three_pl",
                "3pl",
                "3PL",
                "third_party_logistics",
                "logistics_provider"
            ]
        )

        delay_column = self._find_column(
            orders,
            [
                "delay_days",
                "delay",
                "delivery_delay",
                "days_late"
            ]
        )

        required = [
            "order_id",
            "late_order"
        ]

        missing = [
            column
            for column in required
            if column not in orders.columns
        ]

        if three_pl_column is None:
            missing.append("3PL column")

        if delay_column is None:
            missing.append("delay column")

        if missing:
            raise ValueError(
                f"Missing delivery-risk columns: {missing}. "
                f"Available columns: {list(orders.columns)}"
            )

        df = orders.copy()

        df["late_order"] = pd.to_numeric(
            df["late_order"],
            errors="coerce"
        ).fillna(0)

        df[delay_column] = pd.to_numeric(
            df[delay_column],
            errors="coerce"
        ).fillna(0)

        result = (
            df.groupby(three_pl_column)
            .agg(
                total_orders=("order_id", "count"),
                late_orders=("late_order", "sum"),
                avg_delay_days=(delay_column, "mean")
            )
            .reset_index()
        )

        result = result.rename(
            columns={
                three_pl_column: "three_pl"
            }
        )

        result["late_rate"] = (
            result["late_orders"] /
            result["total_orders"]
        )

        late_rate_score = (
            result["late_rate"]
            .clip(0, 1)
            * 100
        )

        delay_score = (
            result["avg_delay_days"]
            .clip(0, 7)
            / 7
            * 100
        )

        result["risk_score"] = (
            late_rate_score * 0.60
            + delay_score * 0.40
        ).round(2)

        result["risk_level"] = result["risk_score"].apply(
            calculate_risk_level
        )

        result["risk_reason"] = result.apply(
            lambda row: (
                f"Late rate={row['late_rate']:.2%}; "
                f"average delay={row['avg_delay_days']:.2f} days"
            ),
            axis=1
        )

        return (
            result
            .sort_values("risk_score", ascending=False)
            .reset_index(drop=True)
        )