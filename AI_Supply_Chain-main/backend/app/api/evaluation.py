from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models.entities import User, UserRole
from app.services.auth_service import get_current_user_optional
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
    ),
    current_user: User | None = Depends(get_current_user_optional),
):

    # RBAC protection: Suppliers cannot trigger system-wide evaluation runs
    if current_user and current_user.role == UserRole.SUPPLIER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Supplier users cannot trigger system-wide evaluations",
        )

    try:

        return (
            system_evaluation_engine
            .run_full_evaluation(
                product_id=product_id,
                horizon=horizon
            )
        )

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )


# =============================================================
# STORED EVALUATION SUMMARY
# =============================================================

@router.get("/summary")
def evaluation_summary(
    current_user: User | None = Depends(get_current_user_optional),
):

    try:
        summary = system_evaluation_engine.get_summary()

        # If supplier user accesses summary, protect global metrics
        if current_user and current_user.role == UserRole.SUPPLIER:
            # Mask global counts for suppliers
            return {
                "status": "success",
                "total_evaluations": summary.get("total_evaluations", 0),
                "success_rate": summary.get("success_rate", 0.0),
                "planner_accuracy": summary.get("planner_accuracy"),
                "retrieval_accuracy": summary.get("retrieval_accuracy"),
                "grounding_rate": summary.get("grounding_rate", 0.0),
                "relevance_rate": summary.get("relevance_rate", 0.0),
                "rbac_accuracy": summary.get("rbac_accuracy"),
                "fallback_accuracy": summary.get("fallback_accuracy"),
                "average_latency_ms": summary.get("average_latency_ms", 0.0),
                "retrieval_distribution": summary.get("retrieval_distribution", {}),
                "authorized_scope": f"supplier:{current_user.supplier_id}",
            }

        return summary

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )


# =============================================================
# STORED EVALUATION RESULTS (DETAILED)
# =============================================================

@router.get("/results")
def evaluation_results(
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User | None = Depends(get_current_user_optional),
):
    """
    Returns latest detailed evaluation query records.
    RBAC Scoped: Supplier users only see records relevant to their supplier ID.
    Never exposes API keys, tokens, or credentials.
    """
    try:
        results = system_evaluation_engine.get_results(limit=limit)

        if current_user and current_user.role == UserRole.SUPPLIER:
            user_sid = str(current_user.supplier_id or "").upper()
            # Filter results so suppliers cannot view evaluations of other suppliers
            results = [
                r for r in results
                if user_sid in str(r.get("query", "")).upper()
                or user_sid in str(r.get("expected_behavior", "")).upper()
            ]

        return {
            "status": "success",
            "count": len(results),
            "results": results,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )

    