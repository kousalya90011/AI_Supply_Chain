from fastapi import APIRouter, HTTPException, Query

from app.services.data_service import DataService
from app.evaluation.forecast_evaluation import ForecastEvaluator
from app.evaluation.query_evaluation import QueryEvaluationEngine
from app.evaluation.system_evaluation import SystemEvaluationEngine


router = APIRouter(
    prefix="/api/evaluation",
    tags=["Evaluation"]
)


data_service = DataService()

forecast_evaluator = ForecastEvaluator()

query_evaluation_engine = QueryEvaluationEngine()

system_evaluation_engine = SystemEvaluationEngine()


# =============================================================
# FORECAST EVALUATION
# =============================================================

@router.get("/forecast/{product_id}")
def evaluate_forecast(
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

        evaluation = forecast_evaluator.evaluate_product(
            demand_df=demand_df,
            product_id=product_id,
            horizon=horizon
        )

        if evaluation["status"] == "not_found":

            raise HTTPException(
                status_code=404,
                detail=evaluation
            )

        if evaluation["status"] == "insufficient_data":

            raise HTTPException(
                status_code=422,
                detail=evaluation
            )

        return evaluation

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )


# =============================================================
# ROUTING EVALUATION
# =============================================================

@router.get("/routing")
def evaluate_routing():

    try:

        return (
            query_evaluation_engine
            .evaluate_routing()
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )


# =============================================================
# COMPLETE SYSTEM EVALUATION
# =============================================================

@router.post("/run")
def run_system_evaluation(
    product_id: str = Query(
        default="P00003"
    ),
    horizon: int = Query(
        default=7,
        ge=1,
        le=30
    )
):

    try:

        return (
            system_evaluation_engine
            .run_full_evaluation(
                product_id=product_id,
                horizon=horizon
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )


# =============================================================
# STORED EVALUATION SUMMARY
# =============================================================

@router.get("/summary")
def evaluation_summary():

    try:

        return (
            system_evaluation_engine
            .get_summary()
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )
    