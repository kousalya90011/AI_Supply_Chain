from __future__ import annotations

import pandas as pd


class DemandRankingAnalyzer:

    """
    Calculates product-level demand ranking.

    Source:
        demand_daily.csv

    Demand definition:
        SUM(demand_units) grouped by product_id.
    """

    def analyze(
        self,
        demand: pd.DataFrame,
        top_n: int | None = None
    ) -> pd.DataFrame:

        if demand is None or demand.empty:

            return pd.DataFrame(
                columns=[
                    "product_id",
                    "total_demand",
                    "average_daily_demand",
                    "demand_days"
                ]
            )

        required_columns = {
            "product_id",
            "demand_units"
        }

        missing = (
            required_columns
            - set(demand.columns)
        )

        if missing:

            raise ValueError(
                "Missing required columns for "
                f"demand analysis: {sorted(missing)}"
            )

        df = demand.copy()

        df["demand_units"] = pd.to_numeric(
            df["demand_units"],
            errors="coerce"
        )

        df = df.dropna(
            subset=[
                "product_id",
                "demand_units"
            ]
        )

        grouped = (
            df.groupby("product_id")
            .agg(
                total_demand=(
                    "demand_units",
                    "sum"
                ),
                average_daily_demand=(
                    "demand_units",
                    "mean"
                ),
                demand_days=(
                    "demand_units",
                    "count"
                )
            )
            .reset_index()
        )

        grouped["total_demand"] = (
            grouped["total_demand"]
            .round(2)
        )

        grouped["average_daily_demand"] = (
            grouped["average_daily_demand"]
            .round(2)
        )

        grouped = grouped.sort_values(
            "total_demand",
            ascending=False
        ).reset_index(
            drop=True
        )

        grouped["demand_rank"] = (
            grouped.index + 1
        )

        if top_n is not None:

            grouped = grouped.head(
                top_n
            )

        return grouped.reset_index(
            drop=True
        )
    