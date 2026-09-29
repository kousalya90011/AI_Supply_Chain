from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Any

from app.analytics.supplier_risk import SupplierRiskAnalyzer
from app.analytics.delivery_risk import DeliveryRiskAnalyzer
from app.analytics.route_risk import RouteRiskAnalyzer
from app.analytics.lead_time_anomaly import LeadTimeAnomalyAnalyzer
from app.analytics.risk_scoring import MAJOR_RISK_LEVELS, NON_MAJOR_RISK_LEVELS


class MajorRisksAnalyzer:
    """
    Synthesizes cross-functional supply chain risks across:
    1. Supplier delivery risk
    2. Inventory / stockout risk
    3. Delivery performance risk
    4. Route risk
    5. Lead-time anomalies

    Supports polarity filtering:
    - condition="major" (default): Focuses on CRITICAL and HIGH severity risk tiers.
    - condition="non_major" (or negative_condition=True): Filters out major tiers and
      evaluates non-major (MEDIUM and LOW risk) operational factors.
    """

    def __init__(self):
        self.supplier_analyzer = SupplierRiskAnalyzer()
        self.delivery_analyzer = DeliveryRiskAnalyzer()
        self.route_analyzer = RouteRiskAnalyzer()
        self.lead_time_analyzer = LeadTimeAnomalyAnalyzer()

    def analyze(
        self,
        datasets: dict[str, pd.DataFrame],
        condition: str = "major",
        negative_condition: bool = False,
    ) -> dict[str, Any]:
        orders = datasets.get("orders_extended")
        if orders is None or orders.empty:
            orders = datasets.get("orders")
        inventory = datasets.get("inventory")

        is_non_major = condition == "non_major" or bool(negative_condition)

        findings = {}
        evidence = []

        # -------------------------------------------------------------
        # 1. Supplier Risk Domain
        # -------------------------------------------------------------
        try:
            sup_df = self.supplier_analyzer.analyze(orders)
            
            if is_non_major:
                # Complement filter: Exclude CRITICAL and HIGH, keep MEDIUM and LOW
                non_major_sups = sup_df[sup_df["risk_level"].isin(NON_MAJOR_RISK_LEVELS)]
                med_sups = sup_df[sup_df["risk_level"] == "MEDIUM"]
                low_sups = sup_df[sup_df["risk_level"] == "LOW"]
                top_sups = non_major_sups.head(5).to_dict(orient="records")

                findings["supplier_risk"] = {
                    "condition": "non_major",
                    "total_evaluated": len(sup_df),
                    "critical_count": 0,
                    "high_count": 0,
                    "medium_count": len(med_sups),
                    "low_count": len(low_sups),
                    "non_major_count": len(non_major_sups),
                    "excluded_major_count": len(sup_df) - len(non_major_sups),
                    "top_risk_suppliers": [
                        {
                            "supplier_id": s["supplier_id"],
                            "risk_score": round(float(s["risk_score"]), 1),
                            "risk_level": s["risk_level"],
                            "late_rate": round(float(s["late_rate"]) * 100.0, 1),
                            "avg_delay": round(float(s.get("avg_delay", 0)), 1),
                            "total_orders": int(s["total_orders"]),
                        }
                        for s in top_sups
                    ],
                }

                for s in top_sups[:3]:
                    evidence.append({
                        "source_type": "analytics",
                        "source_id": f"non_major_risks:supplier:{s['supplier_id']}",
                        "entity_type": "supplier",
                        "entity_id": s["supplier_id"],
                        "metric": "supplier_risk",
                        "risk_level": s["risk_level"],
                        "value": round(float(s["risk_score"]), 1),
                        "data": s,
                        "explanation": f"Supplier {s['supplier_id']} is classified as non-major {s['risk_level']} risk (Score: {s['risk_score']:.1f}, Late Rate: {s['late_rate']*100:.1f}%), within acceptable operational limits.",
                        "retrieval_method": "structured",
                        "confidence": 1.0,
                    })
            else:
                # Major risk filter: CRITICAL and HIGH
                critical_sups = sup_df[sup_df["risk_level"] == "CRITICAL"]
                high_sups = sup_df[sup_df["risk_level"] == "HIGH"]
                top_sups = sup_df.head(5).to_dict(orient="records")

                findings["supplier_risk"] = {
                    "condition": "major",
                    "total_evaluated": len(sup_df),
                    "critical_count": len(critical_sups),
                    "high_count": len(high_sups),
                    "top_risk_suppliers": [
                        {
                            "supplier_id": s["supplier_id"],
                            "risk_score": round(float(s["risk_score"]), 1),
                            "risk_level": s["risk_level"],
                            "late_rate": round(float(s["late_rate"]) * 100.0, 1),
                            "avg_delay": round(float(s.get("avg_delay", 0)), 1),
                            "total_orders": int(s["total_orders"]),
                        }
                        for s in top_sups
                    ],
                }

                for s in top_sups[:3]:
                    evidence.append({
                        "source_type": "analytics",
                        "source_id": f"major_risks:supplier:{s['supplier_id']}",
                        "entity_type": "supplier",
                        "entity_id": s["supplier_id"],
                        "metric": "supplier_risk",
                        "risk_level": s["risk_level"],
                        "value": round(float(s["risk_score"]), 1),
                        "data": s,
                        "explanation": f"Supplier {s['supplier_id']} is classified as {s['risk_level']} risk (Score: {s['risk_score']:.1f}, Late Rate: {s['late_rate']*100:.1f}%).",
                        "retrieval_method": "structured",
                        "confidence": 1.0,
                    })
        except Exception:
            findings["supplier_risk"] = {"error": "Supplier risk analytics unavailable"}

        # -------------------------------------------------------------
        # 2. Inventory / Stockout Risk Domain
        # -------------------------------------------------------------
        try:
            if inventory is not None and not inventory.empty:
                inv_col = "inventory_units" if "inventory_units" in inventory.columns else ("inventory_level" if "inventory_level" in inventory.columns else None)
                demand_col = "demand" if "demand" in inventory.columns else None
                if inv_col and "product_id" in inventory.columns:
                    inv_df = inventory.copy()
                    inv_df[inv_col] = pd.to_numeric(inv_df[inv_col], errors="coerce").fillna(0)
                    inv_agg = inv_df.groupby("product_id").agg(
                        avg_inventory=(inv_col, "mean"),
                        zero_inventory_days=(inv_col, lambda x: int((x <= 0).sum())),
                        total_days=(inv_col, "count"),
                    ).reset_index()
                    inv_agg["stockout_rate"] = inv_agg["zero_inventory_days"] / np.maximum(inv_agg["total_days"], 1)

                    if demand_col and demand_col in inv_df.columns:
                        inv_df[demand_col] = pd.to_numeric(inv_df[demand_col], errors="coerce").fillna(0)
                        dem_agg = inv_df.groupby("product_id")[demand_col].mean().reset_index()
                        inv_agg = inv_agg.merge(dem_agg, on="product_id", how="left")
                        inv_agg["days_of_cover"] = inv_agg["avg_inventory"] / np.maximum(inv_agg[demand_col], 0.1)
                    else:
                        inv_agg["days_of_cover"] = inv_agg["avg_inventory"] / 20.0

                    if is_non_major:
                        # Non-major inventory lines: low stockout rates & healthy cover
                        stable_inv = inv_agg[(inv_agg["stockout_rate"] <= 0.10) & (inv_agg["days_of_cover"] >= 15.0)]
                        if stable_inv.empty:
                            stable_inv = inv_agg.sort_values(by="stockout_rate", ascending=True)
                        top_stockouts = stable_inv.head(5).to_dict(orient="records")

                        findings["inventory_risk"] = {
                            "condition": "non_major",
                            "products_evaluated": len(inv_agg),
                            "stable_inventory_lines": len(stable_inv),
                            "top_stockout_products": [
                                {
                                    "product_id": str(p["product_id"]),
                                    "stockout_rate": round(float(p["stockout_rate"]) * 100.0, 1),
                                    "days_of_cover": round(float(p["days_of_cover"]), 1),
                                    "avg_inventory": round(float(p["avg_inventory"]), 0),
                                }
                                for p in top_stockouts
                            ],
                        }
                        for p in top_stockouts[:3]:
                            evidence.append({
                                "source_type": "analytics",
                                "source_id": f"non_major_risks:inventory:{p['product_id']}",
                                "entity_type": "product",
                                "entity_id": str(p["product_id"]),
                                "metric": "inventory_stockout_risk",
                                "risk_level": "LOW",
                                "value": round(float(p["stockout_rate"]) * 100.0, 1),
                                "data": p,
                                "explanation": f"Product {p['product_id']} maintains non-major inventory risk with {p['stockout_rate']*100:.1f}% stockout rate and {p['days_of_cover']:.1f} days of inventory cover.",
                                "retrieval_method": "structured",
                                "confidence": 1.0,
                            })
                    else:
                        # Highest stockout rate products
                        inv_sorted = inv_agg.sort_values(by="stockout_rate", ascending=False).head(5)
                        top_stockouts = inv_sorted.to_dict(orient="records")

                        findings["inventory_risk"] = {
                            "condition": "major",
                            "products_evaluated": len(inv_agg),
                            "products_with_stockouts": int((inv_agg["stockout_rate"] > 0).sum()),
                            "top_stockout_products": [
                                {
                                    "product_id": str(p["product_id"]),
                                    "stockout_rate": round(float(p["stockout_rate"]) * 100.0, 1),
                                    "days_of_cover": round(float(p["days_of_cover"]), 1),
                                    "avg_inventory": round(float(p["avg_inventory"]), 0),
                                }
                                for p in top_stockouts
                            ],
                        }
                        for p in top_stockouts[:3]:
                            evidence.append({
                                "source_type": "analytics",
                                "source_id": f"major_risks:inventory:{p['product_id']}",
                                "entity_type": "product",
                                "entity_id": str(p["product_id"]),
                                "metric": "inventory_stockout_risk",
                                "risk_level": "HIGH",
                                "value": round(float(p["stockout_rate"]) * 100.0, 1),
                                "data": p,
                                "explanation": f"Product {p['product_id']} has {p['stockout_rate']*100:.1f}% stockout rate and {p['days_of_cover']:.1f} days of inventory cover.",
                                "retrieval_method": "structured",
                                "confidence": 1.0,
                            })
        except Exception:
            findings["inventory_risk"] = {"error": "Inventory risk analytics unavailable"}

        # -------------------------------------------------------------
        # 3. Delivery Performance Risk
        # -------------------------------------------------------------
        try:
            del_df = self.delivery_analyzer.analyze(orders)
            findings["delivery_risk"] = {
                "condition": "non_major" if is_non_major else "major",
                "total_orders_analyzed": len(orders),
                "system_late_rate": round(float(orders["late_order"].mean()) * 100.0, 1) if "late_order" in orders.columns else 0.0,
                "system_avg_delay": round(float(orders["delay_days"].mean()), 1) if "delay_days" in orders.columns else 0.0,
                "top_delivery_risk_entities": del_df.head(3).to_dict(orient="records") if not del_df.empty else [],
            }
        except Exception:
            findings["delivery_risk"] = {"error": "Delivery risk analytics unavailable"}

        # -------------------------------------------------------------
        # 4. Route Risk
        # -------------------------------------------------------------
        try:
            route_df = self.route_analyzer.analyze(orders)
            top_routes = route_df.head(3).to_dict(orient="records") if not route_df.empty else []
            findings["route_risk"] = {
                "condition": "non_major" if is_non_major else "major",
                "routes_evaluated": len(route_df),
                "top_risk_routes": top_routes,
            }
        except Exception:
            findings["route_risk"] = {"error": "Route risk analytics unavailable"}

        # -------------------------------------------------------------
        # 5. Lead Time Anomalies
        # -------------------------------------------------------------
        try:
            lt_res = self.lead_time_analyzer.analyze(orders, top_n=15)
            all_anoms = lt_res.get("findings", [])
            if is_non_major:
                normal_lt = [a for a in all_anoms if a.get("status") == "Normal" or abs(float(a.get("absolute_change_days", 0))) <= 2.0]
                if not normal_lt:
                    normal_lt = sorted(all_anoms, key=lambda x: abs(float(x.get("absolute_change_days", 0))))
                findings["lead_time_anomalies"] = {
                    "condition": "non_major",
                    "anomalies_detected": 0,
                    "stable_suppliers_count": len(normal_lt),
                    "top_anomalies": normal_lt[:3],
                }
                for anom in normal_lt[:2]:
                    evidence.append({
                        "source_type": "analytics",
                        "source_id": f"non_major_risks:lead_time:{anom['supplier_id']}",
                        "entity_type": "supplier",
                        "entity_id": anom["supplier_id"],
                        "metric": "lead_time_anomaly",
                        "risk_level": "Normal",
                        "value": round(float(anom["absolute_change_days"]), 1),
                        "data": anom,
                        "explanation": f"Supplier {anom['supplier_id']} exhibits stable lead-time variance of {anom['absolute_change_days']:+.1f}d ({anom['percentage_change']}%) - {anom['status']}.",
                        "retrieval_method": "structured",
                        "confidence": 1.0,
                    })
            else:
                findings["lead_time_anomalies"] = {
                    "condition": "major",
                    "anomalies_detected": lt_res.get("anomalies_detected", 0),
                    "top_anomalies": all_anoms[:3],
                }
                for anom in all_anoms[:2]:
                    evidence.append({
                        "source_type": "analytics",
                        "source_id": f"major_risks:lead_time:{anom['supplier_id']}",
                        "entity_type": "supplier",
                        "entity_id": anom["supplier_id"],
                        "metric": "lead_time_anomaly",
                        "risk_level": "HIGH",
                        "value": round(float(anom["absolute_change_days"]), 1),
                        "data": anom,
                        "explanation": f"Supplier {anom['supplier_id']} shows a lead time surge of +{anom['absolute_change_days']}d ({anom['percentage_change']}%) - {anom['status']}.",
                        "retrieval_method": "structured",
                        "confidence": 1.0,
                    })
        except Exception:
            findings["lead_time_anomalies"] = {"error": "Lead time anomaly detection unavailable"}

        return {
            "status": "success",
            "condition": "non_major" if is_non_major else "major",
            "negative_condition": is_non_major,
            "findings": findings,
            "evidence": evidence,
        }
