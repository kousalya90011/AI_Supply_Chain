from __future__ import annotations

import pandas as pd


class ProductCostAnalyzer:
    """
    Analyzes product unit cost.

    Supports:
        - cheapest products
        - most expensive products
        - lowest unit cost
        - highest unit cost
    """

    def analyze(
        self,
        products: pd.DataFrame,
        top_n: int | None = None
    ) -> pd.DataFrame:

        if products is None or products.empty:

            return pd.DataFrame(
                columns=[
                    "product_id",
                    "unit_cost",
                ]
            )

        required_columns = {
            "product_id",
            "unit_cost",
        }

        missing = (
            required_columns
            - set(products.columns)
        )

        if missing:

            raise ValueError(
                "Missing required columns for "
                f"product cost analysis: "
                f"{sorted(missing)}"
            )

        df = products.copy()

        df["unit_cost"] = pd.to_numeric(
            df["unit_cost"],
            errors="coerce"
        )

        df = df.dropna(
            subset=[
                "product_id",
                "unit_cost"
            ]
        )

        # -----------------------------------------------------
        # A product may appear more than once in source data.
        # Keep the average unit cost per product.
        # -----------------------------------------------------

        grouped = (
            df.groupby(
                "product_id"
            )
            .agg(
                unit_cost=(
                    "unit_cost",
                    "mean"
                )
            )
            .reset_index()
        )

        grouped["unit_cost"] = (
            grouped["unit_cost"]
            .round(2)
        )

        grouped = (
            grouped
            .sort_values(
                "unit_cost",
                ascending=False
            )
            .reset_index(drop=True)
        )

        grouped["cost_rank"] = (
            grouped.index + 1
        )

        if top_n is not None:

            grouped = grouped.head(
                top_n
            )

        return grouped.reset_index(
            drop=True
        )
