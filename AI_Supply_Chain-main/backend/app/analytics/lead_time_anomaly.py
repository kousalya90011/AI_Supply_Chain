from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Any


class LeadTimeAnomalyAnalyzer:
    """
    Analyzes historical vs. recent supplier lead-time changes and detects
    statistically meaningful lead-time anomalies.
    """

    def analyze(
        self,
        orders: pd.DataFrame,
        supplier_id: str | None = None,
        recent_days: int = 90,
        top_n: int = 15,
        trend: str | None = None,
        operation: str | None = None,
        direction: str | None = None,
    ) -> dict[str, Any]:
        if orders is None or orders.empty:
            return {
                "status": "success",
                "total_suppliers_evaluated": 0,
                "anomalies_detected": 0,
                "findings": [],
                "evidence": [],
            }

        orders_df = orders.copy()
        if "lead_time_days" not in orders_df.columns or "order_date" not in orders_df.columns:
            return {
                "status": "error",
                "message": "Missing lead_time_days or order_date column in orders dataset.",
                "findings": [],
                "evidence": [],
            }

        orders_df["order_date"] = pd.to_datetime(orders_df["order_date"], errors="coerce")
        orders_df["lead_time_days"] = pd.to_numeric(orders_df["lead_time_days"], errors="coerce")
        orders_df = orders_df.dropna(subset=["order_date", "lead_time_days"])

        if supplier_id:
            orders_df = orders_df[
                orders_df["supplier_id"].astype(str).str.upper() == supplier_id.upper()
            ]

        if orders_df.empty:
            return {
                "status": "success",
                "total_suppliers_evaluated": 0,
                "anomalies_detected": 0,
                "findings": [],
                "evidence": [],
            }

        max_date = orders_df["order_date"].max()
        cutoff_date = max_date - pd.Timedelta(days=recent_days)

        historical = orders_df[orders_df["order_date"] < cutoff_date]
        recent = orders_df[orders_df["order_date"] >= cutoff_date]

        hist_agg = historical.groupby("supplier_id")["lead_time_days"].agg(
            hist_avg="mean",
            hist_std="std",
            hist_count="count",
        )

        rec_agg = recent.groupby("supplier_id")["lead_time_days"].agg(
            recent_avg="mean",
            recent_std="std",
            recent_count="count",
        )

        merged = hist_agg.join(rec_agg, how="inner")
        if merged.empty:
            return {
                "status": "success",
                "total_suppliers_evaluated": 0,
                "anomalies_detected": 0,
                "findings": [],
                "evidence": [],
            }

        merged["hist_std"] = merged["hist_std"].fillna(1.0)
        merged["absolute_change"] = merged["recent_avg"] - merged["hist_avg"]
        merged["percentage_change"] = np.where(
            merged["hist_avg"] > 0,
            (merged["absolute_change"] / merged["hist_avg"]) * 100.0,
            0.0,
        )
        
        # Robust z-score of change
        pooled_std = np.maximum(merged["hist_std"], 0.5)
        merged["z_score"] = merged["absolute_change"] / (pooled_std / np.sqrt(np.maximum(merged["recent_count"], 1)))

        def classify_trend(change: float) -> str:
            if change >= 1.5:
                return "Increasing"
            elif change <= -1.5:
                return "Decreasing"
            return "Stable"

        def classify_status(row: pd.Series) -> str:
            chg = row["absolute_change"]
            pct = row["percentage_change"]
            z = row["z_score"]
            if chg >= 4.0 or (pct >= 25.0 and z >= 2.0):
                return "Significant Increase"
            elif chg >= 1.5 or (pct >= 15.0 and z >= 1.5):
                return "Moderate Increase"
            elif chg <= -2.0:
                return "Improving"
            return "Normal"

        merged["trend"] = merged["absolute_change"].apply(classify_trend)
        merged["anomaly_status"] = merged.apply(classify_status, axis=1)
        merged["is_anomaly"] = merged["anomaly_status"].isin(["Significant Increase", "Moderate Increase"])

        # Filter and sort based on trend / direction / operation
        if trend == "decrease" or direction == "ascending":
            merged = merged.sort_values(by="absolute_change", ascending=True)
            # Prioritize negative change if present
            neg_subset = merged[merged["absolute_change"] < 0]
            if not neg_subset.empty:
                merged = neg_subset
        elif trend == "unusual":
            merged = merged.sort_values(by="z_score", ascending=False)
            anom_subset = merged[merged["is_anomaly"]]
            if not anom_subset.empty:
                merged = anom_subset
        else:
            # Increasing or general ranking
            merged = merged.sort_values(by="absolute_change", ascending=False)
            if trend == "increase":
                pos_subset = merged[merged["absolute_change"] > 0]
                if not pos_subset.empty:
                    merged = pos_subset

        if operation == "rank" and (trend == "increase" or direction == "descending") and top_n == 1:
            top_results = merged.head(1).reset_index()
        else:
            top_results = merged.head(top_n).reset_index()

        findings = []
        evidence = []

        for _, row in top_results.iterrows():
            sid = str(row["supplier_id"])
            item = {
                "supplier_id": sid,
                "historical_avg_days": round(float(row["hist_avg"]), 1),
                "recent_avg_days": round(float(row["recent_avg"]), 1),
                "absolute_change_days": round(float(row["absolute_change"]), 1),
                "percentage_change": round(float(row["percentage_change"]), 1),
                "lead_time_std_days": round(float(row["hist_std"]), 1),
                "z_score": round(float(row["z_score"]), 2),
                "observations_historical": int(row["hist_count"]),
                "observations_recent": int(row["recent_count"]),
                "trend": row["trend"],
                "status": row["anomaly_status"],
                "is_anomaly": bool(row["is_anomaly"]),
            }
            findings.append(item)
            evidence.append({
                "source_type": "analytics",
                "source_id": f"lead_time_anomaly:{sid}",
                "entity_type": "supplier",
                "entity_id": sid,
                "metric": "lead_time_anomaly",
                "value": item["absolute_change_days"],
                "data": item,
                "explanation": (
                    f"Supplier {sid} lead time changed from {item['historical_avg_days']}d historically "
                    f"to {item['recent_avg_days']}d recently ({'+' if item['absolute_change_days'] > 0 else ''}"
                    f"{item['absolute_change_days']}d, {item['percentage_change']}% change) - {item['status']}."
                ),
                "retrieval_method": "structured",
                "confidence": 1.0,
            })

        anomaly_count = int(merged["is_anomaly"].sum())

        return {
            "status": "success",
            "total_suppliers_evaluated": len(merged),
            "anomalies_detected": anomaly_count,
            "cutoff_date": cutoff_date.strftime("%Y-%m-%d"),
            "findings": findings,
            "evidence": evidence,
        }
