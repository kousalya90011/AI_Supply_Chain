from __future__ import annotations

import numpy as np
import pandas as pd

from app.analytics.risk_scoring import calculate_risk_level


class InventoryRiskAnalyzer:

    def __init__(self, data_service):
        self.data_service = data_service

    def analyze(
        self,
        top_n: int | None = None
    ) -> pd.DataFrame:

        result = self.data_service.load_data()

        datasets = result.get("datasets", {})

        inventory = datasets.get("inventory")
        demand = datasets.get("demand")

        # ---------------------------------------------------------
        # Validate inventory dataset
        # ---------------------------------------------------------

        if inventory is None:
            raise ValueError(
                "Inventory dataset is not available. "
                "Expected key: 'inventory'."
            )

        if inventory.empty:
            return pd.DataFrame()

        # ---------------------------------------------------------
        # Find required columns
        # ---------------------------------------------------------

        product_col = self._find_column(
            inventory,
            [
                "product_id",
                "product",
                "productid"
            ]
        )

        inventory_col = self._find_column(
            inventory,
            [
                "inventory_units",
                "inventory",
                "stock",
                "stock_units"
            ]
        )

        if product_col is None:
            raise ValueError(
                "Could not find product ID column in inventory dataset."
            )

        if inventory_col is None:
            raise ValueError(
                "Could not find inventory quantity column."
            )

        # ---------------------------------------------------------
        # Clean inventory values
        # ---------------------------------------------------------

        inventory = inventory.copy()

        inventory[inventory_col] = pd.to_numeric(
            inventory[inventory_col],
            errors="coerce"
        ).fillna(0)

        # ---------------------------------------------------------
        # Prepare demand information
        # ---------------------------------------------------------

        demand_summary = pd.DataFrame()

        if demand is not None and not demand.empty:

            demand_product_col = self._find_column(
                demand,
                [
                    "product_id",
                    "product",
                    "productid"
                ]
            )

            demand_value_col = self._find_column(
                demand,
                [
                    "demand",
                    "demand_units",
                    "quantity",
                    "units"
                ]
            )

            if (
                demand_product_col is not None
                and demand_value_col is not None
            ):

                demand = demand.copy()

                demand[demand_value_col] = pd.to_numeric(
                    demand[demand_value_col],
                    errors="coerce"
                ).fillna(0)

                demand_summary = (
                    demand
                    .groupby(demand_product_col)[demand_value_col]
                    .agg(
                        average_daily_demand="mean",
                        total_demand="sum"
                    )
                    .reset_index()
                )

                demand_summary = demand_summary.rename(
                    columns={
                        demand_product_col: "product_id"
                    }
                )

        # ---------------------------------------------------------
        # Aggregate inventory
        # ---------------------------------------------------------

        grouped = (
            inventory
            .groupby(product_col)[inventory_col]
            .agg(
                min_inventory="min",
                avg_inventory="mean",
                total_days="count"
            )
            .reset_index()
        )

        grouped = grouped.rename(
            columns={
                product_col: "product_id"
            }
        )

        # ---------------------------------------------------------
        # Calculate zero inventory days
        # ---------------------------------------------------------

        zero_inventory = (
            inventory[inventory[inventory_col] <= 0]
            .groupby(product_col)
            .size()
            .reset_index(
                name="zero_inventory_days"
            )
        )

        zero_inventory = zero_inventory.rename(
            columns={
                product_col: "product_id"
            }
        )

        grouped = grouped.merge(
            zero_inventory,
            on="product_id",
            how="left"
        )

        grouped["zero_inventory_days"] = (
            grouped["zero_inventory_days"]
            .fillna(0)
        )

        # ---------------------------------------------------------
        # Stockout rate
        # ---------------------------------------------------------

        grouped["stockout_rate"] = (
            grouped["zero_inventory_days"]
            /
            grouped["total_days"].replace(
                0,
                np.nan
            )
        ).fillna(0)

        # ---------------------------------------------------------
        # Merge demand
        # ---------------------------------------------------------

        if not demand_summary.empty:

            grouped = grouped.merge(
                demand_summary,
                on="product_id",
                how="left"
            )

        else:

            grouped["average_daily_demand"] = 0.0
            grouped["total_demand"] = 0.0

        grouped["average_daily_demand"] = (
            grouped["average_daily_demand"]
            .fillna(0)
        )

        grouped["total_demand"] = (
            grouped["total_demand"]
            .fillna(0)
        )

        # ---------------------------------------------------------
        # Days of inventory coverage
        # ---------------------------------------------------------

        grouped["days_of_cover"] = np.where(
            grouped["average_daily_demand"] > 0,

            grouped["avg_inventory"]
            /
            grouped["average_daily_demand"],

            999
        )

        # ---------------------------------------------------------
        # Demand pressure
        # ---------------------------------------------------------

        grouped["demand_pressure"] = np.where(
            (
                grouped["avg_inventory"]
                +
                grouped["average_daily_demand"]
            ) > 0,

            grouped["average_daily_demand"]
            /
            (
                grouped["avg_inventory"]
                +
                grouped["average_daily_demand"]
            ),

            0
        )

        # ---------------------------------------------------------
        # Risk components
        # ---------------------------------------------------------

        grouped["stockout_score"] = (
            grouped["stockout_rate"] * 100
        )

        grouped["demand_pressure_score"] = (
            grouped["demand_pressure"] * 100
        )

        # Lower coverage = higher risk
        grouped["coverage_score"] = (
            100
            -
            (
                np.clip(
                    grouped["days_of_cover"],
                    0,
                    30
                )
                /
                30
                *
                100
            )
        )

        # ---------------------------------------------------------
        # Final risk score
        # ---------------------------------------------------------

        grouped["risk_score"] = (
            0.50 * grouped["stockout_score"]
            +
            0.30 * grouped["demand_pressure_score"]
            +
            0.20 * grouped["coverage_score"]
        )

        grouped["risk_score"] = (
            grouped["risk_score"]
            .clip(0, 100)
            .round(2)
        )

        # ---------------------------------------------------------
        # Risk level
        # ---------------------------------------------------------

        grouped["risk_level"] = (
            grouped["risk_score"]
            .apply(calculate_risk_level)
        )

        # ---------------------------------------------------------
        # Explanation
        # ---------------------------------------------------------

        grouped["risk_reason"] = (
            "Stockout rate="
            +
            (
                grouped["stockout_rate"]
                * 100
            )
            .round(2)
            .astype(str)
            +
            "%; demand pressure="
            +
            (
                grouped["demand_pressure"]
                * 100
            )
            .round(2)
            .astype(str)
            +
            "%; days of cover="
            +
            grouped["days_of_cover"]
            .round(2)
            .astype(str)
        )

        # ---------------------------------------------------------
        # Sort highest risk first
        # ---------------------------------------------------------

        # ---------------------------------------------------------
        # Include catalog products lacking daily inventory telemetry
        # ---------------------------------------------------------
        all_prods = datasets.get("products")
        if all_prods is not None and not all_prods.empty and "product_id" in all_prods.columns:
            known = set(grouped["product_id"].astype(str).str.upper())
            missing = all_prods[~all_prods["product_id"].astype(str).str.upper().isin(known)]
            if not missing.empty:
                extra_rows = []
                for _, mrow in missing.iterrows():
                    extra_rows.append({
                        "product_id": str(mrow["product_id"]).strip().upper(),
                        "min_inventory": 0,
                        "avg_inventory": 0.0,
                        "total_days": 0,
                        "zero_inventory_days": 0,
                        "stockout_days": 0,
                        "stockout_rate": 0.0,
                        "average_daily_demand": 0.0,
                        "total_demand": 0.0,
                        "days_of_cover": 999.0,
                        "demand_pressure": 0.0,
                        "stockout_score": 0.0,
                        "demand_pressure_score": 0.0,
                        "coverage_score": 0.0,
                        "risk_score": 15.0,
                        "risk_level": "LOW",
                        "risk_reason": "Newly cataloged product in approved status awaiting initial warehouse stock.",
                    })
                if extra_rows:
                    grouped = pd.concat([grouped, pd.DataFrame(extra_rows)], ignore_index=True)

        if top_n is not None:
            grouped = grouped.head(top_n)

        return grouped.reset_index(drop=True)

    # =============================================================
    # Utility
    # =============================================================

    def _find_column(
        self,
        df: pd.DataFrame,
        candidates: list[str]
    ) -> str | None:

        normalized = {
            str(column).strip().lower(): column
            for column in df.columns
        }

        for candidate in candidates:

            key = candidate.strip().lower()

            if key in normalized:
                return normalized[key]

        return None