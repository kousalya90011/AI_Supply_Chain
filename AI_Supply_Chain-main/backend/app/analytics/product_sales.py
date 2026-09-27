from __future__ import annotations

import pandas as pd


class ProductSalesAnalyzer:
    """
    Calculates product-level sales/revenue from order_value.

    Source:
        orders_extended.order_value

    Sales definition:
        Total order_value aggregated by product_id.
    """

    def analyze(self, orders: pd.DataFrame, top_n: int | None = None) -> pd.DataFrame:
        if orders is None or orders.empty:
            return pd.DataFrame(
                columns=[
                    "product_id",
                    "total_sales",
                    "total_units",
                    "order_count",
                    "average_order_value",
                ]
            )

        required_columns = {
            "product_id",
            "order_value",
            "units",
        }

        missing = required_columns - set(orders.columns)

        if missing:
            raise ValueError(
                f"Missing required columns for sales analysis: {sorted(missing)}"
            )

        df = orders.copy()

        df["order_value"] = pd.to_numeric(
            df["order_value"],
            errors="coerce"
        )

        df["units"] = pd.to_numeric(
            df["units"],
            errors="coerce"
        )

        df = df.dropna(
            subset=[
                "product_id",
                "order_value"
            ]
        )

        grouped = (
            df.groupby("product_id")
            .agg(
                total_sales=("order_value", "sum"),
                total_units=("units", "sum"),
                order_count=("product_id", "count"),
                average_order_value=("order_value", "mean"),
            )
            .reset_index()
        )

        grouped["total_sales"] = grouped["total_sales"].round(2)
        grouped["total_units"] = grouped["total_units"].round(2)
        grouped["average_order_value"] = (
            grouped["average_order_value"].round(2)
        )

        grouped = grouped.sort_values(
            "total_sales",
            ascending=False
        ).reset_index(drop=True)

        grouped["sales_rank"] = (
            grouped.index + 1
        )

        if top_n is not None:
            grouped = grouped.head(top_n)

        return grouped.reset_index(drop=True)
    