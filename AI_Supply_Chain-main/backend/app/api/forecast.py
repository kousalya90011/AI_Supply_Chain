from fastapi import APIRouter, HTTPException, Query

from app.services.data_service import DataService
from app.analytics.forecasting import DemandForecaster


router = APIRouter(
    prefix="/api/forecast",
    tags=["Forecast"]
)

data_service = DataService()
forecaster = DemandForecaster()


@router.get("/products")
def forecastable_products():

    try:

        result = data_service.load_data()

        demand_df = result["datasets"]["demand"]

        products = (
            forecaster
            .get_available_products(demand_df)
        )

        return {
            "status": "success",
            "count": len(products),
            "products": products
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )


@router.get("/product/{product_id}")
def forecast_product(
    product_id: str,
    horizon: int = Query(
        default=7,
        ge=1,
        le=30
    )
):

    try:

        result = data_service.load_data()

        demand_df = result["datasets"]["demand"]

        forecast = forecaster.forecast_product(
            demand_df=demand_df,
            product_id=product_id,
            horizon=horizon
        )

        if forecast["status"] == "not_found":

            raise HTTPException(
                status_code=404,
                detail=forecast
            )

        if forecast["status"] == "insufficient_data":

            raise HTTPException(
                status_code=422,
                detail=forecast
            )

        return forecast

    except HTTPException:

        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )
    