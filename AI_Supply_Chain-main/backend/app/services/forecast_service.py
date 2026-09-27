from app.services.data_service import DataService
from app.analytics.forecasting import DemandForecaster


class ForecastService:

    def __init__(self):

        self.data_service = DataService()

        self.forecaster = DemandForecaster()

    def forecast_product(
        self,
        product_id: str,
        horizon: int = 7
    ) -> dict:

        datasets = (
            self.data_service
            .load_data()["datasets"]
        )

        demand = datasets["demand"]

        return self.forecaster.forecast_product(
            demand=demand,
            product_id=product_id,
            horizon=horizon
        )
    