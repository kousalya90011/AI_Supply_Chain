from __future__ import annotations

import numpy as np
import pandas as pd

from app.analytics.forecasting import DemandForecaster


class ForecastEvaluator:

    def __init__(self):
        self.forecaster = DemandForecaster()

    def _prepare_data(
        self,
        demand_df: pd.DataFrame
    ) -> pd.DataFrame:

        df = self.forecaster._prepare_demand_data(
            demand_df
        )

        return df

    def evaluate_product(
        self,
        demand_df: pd.DataFrame,
        product_id: str,
        horizon: int = 7
    ) -> dict:

        df = self._prepare_data(demand_df)

        product_df = df[
            df["product_id"] == str(product_id)
        ].copy()

        if product_df.empty:

            return {
                "status": "not_found",
                "product_id": product_id,
                "message": (
                    f"No demand data found for {product_id}"
                )
            }

        product_df = (
            product_df
            .groupby("date", as_index=False)["demand"]
            .sum()
            .sort_values("date")
        )

        if len(product_df) <= horizon + 30:

            return {
                "status": "insufficient_data",
                "product_id": product_id,
                "historical_points": len(product_df),
                "message": (
                    "Not enough data for forecast evaluation."
                )
            }

        # Hold out the last N days
        train = product_df.iloc[:-horizon].copy()
        test = product_df.iloc[-horizon:].copy()

        # Use the same forecasting logic
        forecast_result = self.forecaster.forecast_product(
            demand_df=train.assign(
                product_id=product_id
            ),
            product_id=product_id,
            horizon=horizon
        )

        predictions = np.array([
            item["predicted_demand"]
            for item in forecast_result["forecast"]
        ])

        actuals = test["demand"].to_numpy(
            dtype=float
        )

        errors = actuals - predictions

        mae = np.mean(
            np.abs(errors)
        )

        rmse = np.sqrt(
            np.mean(errors ** 2)
        )

        non_zero = actuals != 0

        if np.any(non_zero):

            mape = np.mean(
                np.abs(
                    errors[non_zero]
                    / actuals[non_zero]
                )
            ) * 100

        else:

            mape = None

        comparison = []

        for i in range(len(test)):

            comparison.append(
                {
                    "date": test.iloc[i]["date"].strftime(
                        "%Y-%m-%d"
                    ),
                    "actual": round(
                        float(actuals[i]),
                        2
                    ),
                    "predicted": round(
                        float(predictions[i]),
                        2
                    ),
                    "error": round(
                        float(errors[i]),
                        2
                    )
                }
            )

        return {
            "status": "success",
            "product_id": product_id,
            "horizon": horizon,
            "training_points": len(train),
            "test_points": len(test),
            "metrics": {
                "mae": round(float(mae), 4),
                "rmse": round(float(rmse), 4),
                "mape": (
                    round(float(mape), 4)
                    if mape is not None
                    else None
                )
            },
            "actual_vs_predicted": comparison
        }
    