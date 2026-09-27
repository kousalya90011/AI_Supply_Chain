from __future__ import annotations

import numpy as np
import pandas as pd


class DemandForecaster:

    def _find_column(
        self,
        df: pd.DataFrame,
        candidates: list[str]
    ) -> str | None:

        normalized = {
            str(col).strip().lower(): col
            for col in df.columns
        }

        for candidate in candidates:

            key = candidate.strip().lower()

            if key in normalized:
                return normalized[key]

        return None

    def _prepare_demand_data(
        self,
        demand_df: pd.DataFrame
    ) -> pd.DataFrame:

        product_col = self._find_column(
            demand_df,
            [
                "product_id",
                "product",
                "productid"
            ]
        )

        date_col = self._find_column(
            demand_df,
            [
                "date",
                "demand_date",
                "day",
                "timestamp"
            ]
        )

        demand_col = self._find_column(
            demand_df,
            [
                "demand",
                "demand_units",
                "quantity",
                "units"
            ]
        )

        if product_col is None:
            raise ValueError(
                f"Product column not found. "
                f"Available columns: {list(demand_df.columns)}"
            )

        if date_col is None:
            raise ValueError(
                f"Date column not found. "
                f"Available columns: {list(demand_df.columns)}"
            )

        if demand_col is None:
            raise ValueError(
                f"Demand column not found. "
                f"Available columns: {list(demand_df.columns)}"
            )

        df = demand_df[
            [product_col, date_col, demand_col]
        ].copy()

        df.columns = [
            "product_id",
            "date",
            "demand"
        ]

        df["product_id"] = (
            df["product_id"]
            .astype(str)
            .str.strip()
        )

        df["date"] = pd.to_datetime(
            df["date"],
            errors="coerce"
        )

        df["demand"] = pd.to_numeric(
            df["demand"],
            errors="coerce"
        )

        df = df.dropna(
            subset=[
                "product_id",
                "date",
                "demand"
            ]
        )

        df = df.sort_values("date")

        return df

    def get_available_products(
        self,
        demand_df: pd.DataFrame
    ) -> list[str]:

        df = self._prepare_demand_data(demand_df)

        return sorted(
            df["product_id"]
            .unique()
            .tolist()
        )

    def forecast_product(
        self,
        demand_df: pd.DataFrame,
        product_id: str,
        horizon: int = 7
    ) -> dict:

        df = self._prepare_demand_data(demand_df)

        product_id = str(product_id).strip()

        product_df = df[
            df["product_id"] == product_id
        ].copy()

        if product_df.empty:

            available = (
                df["product_id"]
                .unique()
                .tolist()
            )

            return {
                "status": "not_found",
                "product_id": product_id,
                "message": (
                    f"No demand data found for {product_id}"
                ),
                "available_products_count": len(
                    available
                ),
                "sample_available_products": sorted(
                    available
                )[:20]
            }

        product_df = (
            product_df
            .groupby("date", as_index=False)["demand"]
            .sum()
            .sort_values("date")
        )

        if len(product_df) < 3:

            return {
                "status": "insufficient_data",
                "product_id": product_id,
                "message": (
                    "Not enough historical demand data "
                    "to generate a forecast."
                ),
                "historical_points": len(product_df)
            }

        # Use the most recent 30 observations
        # for a simple and explainable forecast.
        window = min(30, len(product_df))

        recent = product_df.tail(window).copy()

        y = recent["demand"].to_numpy(
            dtype=float
        )

        x = np.arange(len(y))

        # Linear trend
        slope, intercept = np.polyfit(
            x,
            y,
            1
        )

        future_x = np.arange(
            len(y),
            len(y) + horizon
        )

        predictions = (
            intercept +
            slope * future_x
        )

        # Demand cannot be negative.
        predictions = np.maximum(
            predictions,
            0
        )

        last_date = product_df["date"].max()

        future_dates = pd.date_range(
            start=last_date + pd.Timedelta(days=1),
            periods=horizon,
            freq="D"
        )

        forecast = []

        for date, value in zip(
            future_dates,
            predictions
        ):

            forecast.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "predicted_demand": round(
                        float(value),
                        2
                    )
                }
            )

        return {
            "status": "success",
            "product_id": product_id,
            "historical_points": len(product_df),
            "training_window": window,
            "last_historical_date": (
                last_date.strftime("%Y-%m-%d")
            ),
            "average_recent_demand": round(
                float(np.mean(y)),
                2
            ),
            "trend_per_day": round(
                float(slope),
                4
            ),
            "forecast": forecast
        }
    