from __future__ import annotations

import numpy as np
import pandas as pd

from fastapi import (
    APIRouter,
    HTTPException,
    Query
)

from app.services.analytics_service import AnalyticsService
from app.analytics.route_risk import RouteRiskAnalyzer
from app.analytics.anomaly_detection import AnomalyDetector
from app.services.evidence_service import EvidenceService


router = APIRouter(
    prefix="/api/analytics",
    tags=["Analytics"]
)

service = AnalyticsService()
route_analyzer = RouteRiskAnalyzer()
anomaly_detector = AnomalyDetector()
evidence_service = EvidenceService()


@router.get("/dashboard")
def dashboard():

    return service.dashboard_metrics()


@router.get("/supplier-risk")
def supplier_risk(limit: int | None = None):

    df = service.supplier_risk()

    if limit is not None and limit > 0:
        return df.head(limit).to_dict(
            orient="records"
        )

    return df.to_dict(
        orient="records"
    )


@router.get("/delivery-risk")
def delivery_risk():

    df = service.delivery_risk()

    return df.head(20).to_dict(
        orient="records"
    )


    # @router.get("/inventory-risk")
    # def inventory_risk():

    #     df = service.inventory_risk()

    #     return df.head().to_dict(
    #         orient="records"
    #     )
@router.get("/inventory-risk")
def inventory_risk(
    top_n: int = Query(
        default=2000,
        ge=1,
        le=2000,
        description="Number of products to return"
    )
):
    try:
        df = service.inventory_risk(top_n=top_n)

        if df is None:
            return []

        # If the service returns a DataFrame
        if hasattr(df, "replace") and hasattr(df, "to_dict"):
            df = df.replace([np.inf, -np.inf], np.nan)
            df = df.fillna(0)

            return df.head(top_n).to_dict(
                orient="records"
            )

        # If service already returns a list
        return df

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )

@router.get("/route-risk")
def route_risk():

    try:

        result = service.get_data()

        df = route_analyzer.analyze(
            result["datasets"]["orders_extended"]
        )

        return df.head(20).to_dict(
            orient="records"
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )

@router.get("/anomalies/orders")
def order_anomalies():

    try:

        result = service.get_data()

        orders = result["datasets"]["orders_extended"]

        numeric_column = None

        for candidate in [
            "delay_days",
            "delay",
            "delivery_delay",
            "days_late",
            "units"
        ]:

            if candidate in orders.columns:

                numeric_column = candidate
                break

        if numeric_column is None:

            raise ValueError(
                "No suitable numeric anomaly column found"
            )

        summary = anomaly_detector.summarize(
            orders,
            numeric_column
        )

        return summary

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )
@router.get("/evidence/supplier/{supplier_id}")
def supplier_evidence(
    supplier_id: str
):

    try:

        return evidence_service.supplier_evidence(
            supplier_id
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )
@router.get("/evidence/product/{product_id}")
def product_evidence(
    product_id: str
):

    try:

        return evidence_service.inventory_evidence(
            product_id
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )

@router.get("/product-sales")
def product_sales(
    top_n: int | None = Query(
        default=None,
        ge=1,
        description="Optional number of highest-sales products to return."
    )
):
    try:
        df = service.product_sales(top_n=top_n)

        if df is None or df.empty:
            return {
                "status": "success",
                "total_products": 0,
                "records": []
            }

        records = df.to_dict(orient="records")

        return {
            "status": "success",
            "products_returned": len(records),
            "total_products": int(
                df["product_id"].nunique()
            ),
            "records": records
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )
    