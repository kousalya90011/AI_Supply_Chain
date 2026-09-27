from __future__ import annotations

import pandas as pd

from app.analytics.risk_scoring import (
    RiskScoringEngine,
    calculate_risk_level
)


class RouteRiskAnalyzer:

    def __init__(self):

        self.scorer = RiskScoringEngine()

    def analyze(
        self,
        orders: pd.DataFrame
    ) -> pd.DataFrame:

        if orders is None or orders.empty:
            return pd.DataFrame()

        # ---------------------------------------------------------
        # Find route column
        # ---------------------------------------------------------

        route_column = None

        for candidate in [
            "route_id",
            "route",
            "transport_route"
        ]:

            if candidate in orders.columns:
                route_column = candidate
                break

        if route_column is None:

            raise ValueError(
                "No route column found. "
                f"Available columns: {list(orders.columns)}"
            )

        # ---------------------------------------------------------
        # Validate required columns
        # ---------------------------------------------------------

        required = [
            "order_id",
            "late_order"
        ]

        missing = [
            column
            for column in required
            if column not in orders.columns
        ]

        if missing:

            raise ValueError(
                f"Missing route-risk columns: {missing}"
            )

        # ---------------------------------------------------------
        # Prepare data
        # ---------------------------------------------------------

        df = orders.copy()

        df["late_order"] = pd.to_numeric(
            df["late_order"],
            errors="coerce"
        ).fillna(0)

        # ---------------------------------------------------------
        # Aggregate by route
        # ---------------------------------------------------------

        result = (
            df.groupby(route_column)
            .agg(
                total_orders=(
                    "order_id",
                    "count"
                ),
                late_orders=(
                    "late_order",
                    "sum"
                )
            )
            .reset_index()
        )

        result = result.rename(
            columns={
                route_column: "route_id"
            }
        )

        # ---------------------------------------------------------
        # Late rate
        # ---------------------------------------------------------

        result["late_rate"] = (
            result["late_orders"]
            /
            result["total_orders"]
            .replace(0, 1)
        )

        # ---------------------------------------------------------
        # Risk score
        #
        # Project heuristic:
        # late rate × 100
        # ---------------------------------------------------------

        result["risk_score"] = (
            result["late_rate"]
            .clip(0, 1)
            * 100
        ).round(2)

        # ---------------------------------------------------------
        # Risk level
        # ---------------------------------------------------------

        result["risk_level"] = (
            result["risk_score"]
            .apply(calculate_risk_level)
        )

        # ---------------------------------------------------------
        # Explanation
        # ---------------------------------------------------------

        result["risk_reason"] = result.apply(
            lambda row: (
                f"Route late rate="
                f"{row['late_rate']:.2%}"
            ),
            axis=1
        )

        # ---------------------------------------------------------
        # Sort highest risk first
        # ---------------------------------------------------------

        return (
            result
            .sort_values(
                "risk_score",
                ascending=False
            )
            .reset_index(drop=True)
        )
    