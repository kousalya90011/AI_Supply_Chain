from __future__ import annotations

from app.analytics.forecasting import DemandForecaster


class ForecastAgent:

    def __init__(self, data_service):
        self.data_service = data_service
        self.forecaster = DemandForecaster()

    def run(
        self,
        product_id: str,
        horizon: int = 7
    ) -> dict:

        # -----------------------------------------------------
        # Validate product ID
        # -----------------------------------------------------

        if not product_id:

            return {
                "status": "error",
                "message": (
                    "Product ID is required for forecasting."
                )
            }

        try:

            # -------------------------------------------------
            # Load datasets
            # -------------------------------------------------

            datasets = (
                self.data_service
                .load_data()
                .get("datasets", {})
            )

            demand = datasets.get("demand")

            if demand is None or demand.empty:

                return {
                    "status": "error",
                    "message": (
                        "Demand dataset is not available."
                    )
                }

            # -------------------------------------------------
            # Use the actual DemandForecaster method
            # -------------------------------------------------

            result = self.forecaster.forecast_product(
                demand_df=demand,
                product_id=product_id,
                horizon=horizon
            )

            # -------------------------------------------------
            # Handle forecasting failure
            # -------------------------------------------------

            if result.get("status") != "success":
                return result

            # -------------------------------------------------
            # Build structured evidence
            # -------------------------------------------------

            evidence = {
                "product_id": result.get(
                    "product_id",
                    product_id
                ),

                "historical_points": result.get(
                    "historical_points"
                ),

                "training_window": result.get(
                    "training_window"
                ),

                "last_historical_date": result.get(
                    "last_historical_date"
                ),

                "average_recent_demand": result.get(
                    "average_recent_demand"
                ),

                "trend_per_day": result.get(
                    "trend_per_day"
                ),

                "forecast": result.get(
                    "forecast",
                    []
                )
            }

            # -------------------------------------------------
            # Return common agent structure
            # -------------------------------------------------

            return {
                "status": "success",

                "agent": (
                    "Demand Forecast Agent"
                ),

                "entity_id": product_id,

                "findings": [
                    evidence
                ],

                "evidence": [
                    evidence
                ],

                "source": {
                    "dataset": "demand_daily",
                    "method": "linear_trend",
                    "training_window": result.get(
                        "training_window"
                    ),
                    "forecast_horizon": horizon
                }
            }

        except Exception as exc:

            return {
                "status": "error",
                "message": str(exc)
            }
        