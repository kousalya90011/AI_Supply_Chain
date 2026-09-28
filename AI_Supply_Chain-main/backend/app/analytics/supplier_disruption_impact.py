from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Any


class SupplierDisruptionImpactAnalyzer:
    """
    Analyzes which products are most vulnerable to supplier disruptions
    by connecting:
    Supplier Disruption -> Products Supplied -> Orders/Volume -> Demand -> Inventory -> Stockout Exposure.
    """

    def analyze(
        self,
        datasets: dict[str, pd.DataFrame],
        supplier_id: str | None = None,
        product_id: str | None = None,
        top_n: int = 10,
    ) -> dict[str, Any]:
        orders = datasets.get("orders_extended")
        if orders is None or orders.empty:
            orders = datasets.get("orders")

        inventory = datasets.get("inventory")
        products = datasets.get("products")
        suppliers = datasets.get("suppliers")

        if orders is None or orders.empty:
            return {
                "status": "success",
                "findings": [],
                "evidence": [],
            }

        orders_df = orders.copy()

        # Filter if requested
        if supplier_id:
            orders_df = orders_df[
                orders_df["supplier_id"].astype(str).str.upper() == supplier_id.upper()
            ]
        if product_id:
            orders_df = orders_df[
                orders_df["product_id"].astype(str).str.upper() == product_id.upper()
            ]

        if orders_df.empty:
            return {
                "status": "success",
                "findings": [],
                "evidence": [],
            }

        # 1. Supplier Disruption Metrics
        sup_aggs = {
            "total_orders": ("order_id", "count"),
            "late_orders": ("late_order", "sum"),
        }
        if "disruption_flag" in orders_df.columns:
            sup_aggs["disruption_rate"] = ("disruption_flag", "mean")
        else:
            sup_aggs["disruption_rate"] = ("late_order", lambda x: (x.sum() / max(len(x), 1)) * 0.5)

        if "delay_days" in orders_df.columns:
            sup_aggs["avg_delay"] = ("delay_days", "mean")

        sup_perf = orders_df.groupby("supplier_id").agg(**sup_aggs).reset_index()
        sup_perf["late_rate"] = sup_perf["late_orders"] / np.maximum(sup_perf["total_orders"], 1)
        if "avg_delay" not in sup_perf.columns:
            sup_perf["avg_delay"] = 0.0

        # Assign supplier risk level based on operational features
        def calc_sup_risk(row: pd.Series) -> tuple[float, str]:
            score = (
                row["late_rate"] * 45.0
                + (row["disruption_rate"] * 35.0)
                + min(row["avg_delay"] * 3.0, 20.0)
            )
            score = float(np.clip(score, 0.0, 100.0))
            if score >= 80.0:
                return score, "CRITICAL"
            elif score >= 60.0:
                return score, "HIGH"
            elif score >= 30.0:
                return score, "MEDIUM"
            return score, "LOW"

        risk_tuples = sup_perf.apply(calc_sup_risk, axis=1)
        sup_perf["supplier_risk_score"] = [r[0] for r in risk_tuples]
        sup_perf["supplier_risk_level"] = [r[1] for r in risk_tuples]

        # 2. Product-Supplier Aggregations
        prod_sup = orders_df.groupby(["product_id", "supplier_id"]).agg(
            prod_orders=("order_id", "count"),
            prod_units=("units", "sum"),
            prod_late_orders=("late_order", "sum"),
        ).reset_index()
        prod_sup["prod_late_rate"] = prod_sup["prod_late_orders"] / np.maximum(prod_sup["prod_orders"], 1)

        # Merge supplier metrics into product-supplier pairs
        merged = prod_sup.merge(sup_perf, on="supplier_id", how="left")

        # 3. Product Inventory & Demand Metrics
        inv_by_prod = {}
        if inventory is not None and not inventory.empty:
            inv_col = "inventory_units" if "inventory_units" in inventory.columns else ("inventory_level" if "inventory_level" in inventory.columns else None)
            demand_col = "demand" if "demand" in inventory.columns else None

            if inv_col and "product_id" in inventory.columns:
                inv_df = inventory.copy()
                inv_df[inv_col] = pd.to_numeric(inv_df[inv_col], errors="coerce").fillna(0)
                
                inv_agg = inv_df.groupby("product_id").agg(
                    avg_inventory=(inv_col, "mean"),
                    min_inventory=(inv_col, "min"),
                    zero_inventory_days=(inv_col, lambda x: int((x <= 0).sum())),
                    days_tracked=(inv_col, "count"),
                ).reset_index()

                inv_agg["stockout_rate"] = inv_agg["zero_inventory_days"] / np.maximum(inv_agg["days_tracked"], 1)

                if demand_col and demand_col in inv_df.columns:
                    inv_df[demand_col] = pd.to_numeric(inv_df[demand_col], errors="coerce").fillna(0)
                    dem_agg = inv_df.groupby("product_id")[demand_col].mean().reset_index()
                    dem_agg.rename(columns={demand_col: "avg_daily_demand"}, inplace=True)
                    inv_agg = inv_agg.merge(dem_agg, on="product_id", how="left")
                else:
                    inv_agg["avg_daily_demand"] = 25.0

                inv_agg["days_of_cover"] = np.where(
                    inv_agg["avg_daily_demand"] > 0,
                    inv_agg["avg_inventory"] / inv_agg["avg_daily_demand"],
                    30.0,
                )
                inv_by_prod = inv_agg.set_index("product_id").to_dict(orient="index")

        # Merge inventory metrics
        merged["avg_inventory"] = merged["product_id"].map(lambda p: inv_by_prod.get(p, {}).get("avg_inventory", 150.0))
        merged["avg_daily_demand"] = merged["product_id"].map(lambda p: inv_by_prod.get(p, {}).get("avg_daily_demand", 20.0))
        merged["days_of_cover"] = merged["product_id"].map(lambda p: inv_by_prod.get(p, {}).get("days_of_cover", 15.0))
        merged["stockout_rate"] = merged["product_id"].map(lambda p: inv_by_prod.get(p, {}).get("stockout_rate", 0.05))

        # 4. Exposure Score Calculation
        # Vulnerability = high supplier disruption + high late rate + low days of cover + high stockout rate
        cover_penalty = np.clip((30.0 - merged["days_of_cover"]) / 30.0, 0.0, 1.0)
        
        merged["exposure_score"] = (
            (merged["disruption_rate"] * 35.0)
            + (merged["late_rate"] * 25.0)
            + (cover_penalty * 25.0)
            + (merged["stockout_rate"] * 15.0)
        ) * 100.0 / 100.0

        merged["exposure_score"] = merged["exposure_score"].clip(0.0, 100.0).round(1)

        # Sort products by disruption exposure score
        merged = merged.sort_values(by="exposure_score", ascending=False)
        top_products = merged.head(top_n).reset_index(drop=True)

        findings = []
        evidence = []

        for idx, row in top_products.iterrows():
            pid = str(row["product_id"])
            sid = str(row["supplier_id"])
            item = {
                "rank": idx + 1,
                "product_id": pid,
                "supplier_id": sid,
                "supplier_risk_level": row["supplier_risk_level"],
                "disruption_rate": round(float(row["disruption_rate"]) * 100.0, 1),
                "supplier_late_rate": round(float(row["late_rate"]) * 100.0, 1),
                "avg_daily_demand": round(float(row["avg_daily_demand"]), 1),
                "inventory_units": round(float(row["avg_inventory"]), 0),
                "days_of_cover": round(float(row["days_of_cover"]), 1),
                "stockout_rate": round(float(row["stockout_rate"]) * 100.0, 1),
                "exposure_score": float(row["exposure_score"]),
            }
            findings.append(item)
            evidence.append({
                "source_type": "analytics",
                "source_id": f"product_disruption_impact:{pid}",
                "entity_type": "product",
                "entity_id": pid,
                "metric": "supplier_disruption_impact",
                "value": item["exposure_score"],
                "data": item,
                "explanation": (
                    f"Product {pid} supplied by {sid} ({item['supplier_risk_level']} risk) has "
                    f"{item['disruption_rate']}% supplier disruption rate, {item['days_of_cover']} days of cover, "
                    f"and {item['stockout_rate']}% historical stockout rate (Exposure Score: {item['exposure_score']}/100)."
                ),
                "retrieval_method": "structured",
                "confidence": 1.0,
            })

        return {
            "status": "success",
            "total_products_evaluated": len(merged),
            "findings": findings,
            "evidence": evidence,
        }
