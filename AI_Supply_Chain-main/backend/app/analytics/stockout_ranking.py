from __future__ import annotations

import pandas as pd


class StockoutRankingAnalyzer:

    """
    Calculates product-level stockout ranking.

    Stockout definition:
        inventory_units <= 0

    Stockout rate:
        zero_inventory_days / total_inventory_days
    """

    def analyze(
        self,
        inventory: pd.DataFrame,
        top_n: int | None = None
    ) -> pd.DataFrame:

        if inventory is None or inventory.empty:

            return pd.DataFrame(
                columns=[
                    "product_id",
                    "total_days",
                    "zero_inventory_days",
                    "stockout_rate",
                    "stockout_rank"
                ]
            )

        required_columns = {
            "product_id",
            "inventory_units"
        }

        missing = (
            required_columns
            - set(inventory.columns)
        )

        if missing:

            raise ValueError(
                "Missing required columns for "
                f"stockout analysis: {sorted(missing)}"
            )

        df = inventory.copy()

        df["inventory_units"] = pd.to_numeric(
            df["inventory_units"],
            errors="coerce"
        )

        df = df.dropna(
            subset=[
                "product_id",
                "inventory_units"
            ]
        )

        df["stockout"] = (
            df["inventory_units"] <= 0
        ).astype(int)

        grouped = (
            df.groupby("product_id")
            .agg(
                total_days=(
                    "inventory_units",
                    "count"
                ),
                zero_inventory_days=(
                    "stockout",
                    "sum"
                ),
                average_inventory=(
                    "inventory_units",
                    "mean"
                )
            )
            .reset_index()
        )

        grouped["stockout_rate"] = (
            grouped["zero_inventory_days"]
            / grouped["total_days"]
        )

        grouped["stockout_rate"] = (
            grouped["stockout_rate"]
            .round(4)
        )

        grouped["average_inventory"] = (
            grouped["average_inventory"]
            .round(2)
        )

        grouped = grouped.sort_values(
            "stockout_rate",
            ascending=False
        ).reset_index(
            drop=True
        )

        grouped["stockout_rank"] = (
            grouped.index + 1
        )

        if top_n is not None:

            grouped = grouped.head(
                top_n
            )

        return grouped.reset_index(
            drop=True
        )
    