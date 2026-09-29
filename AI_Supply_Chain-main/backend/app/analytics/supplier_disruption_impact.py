from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Any


class SupplierDisruptionImpactAnalyzer:
    """
    Analyzes which products and suppliers are affected vs not affected by supplier disruptions.
    Connects:
    Supplier Disruption -> Products Supplied -> Orders/Volume -> Demand -> Inventory -> Stockout Exposure.

    Supports:
    - Establishing complete product population (2,000 products) and supplier population (150 suppliers)
    - Deterministic identification of affected items meeting disruption impact criteria
    - Derivation of unaffected items via set difference:
      Unaffected Items = Complete Population - Affected Set
    - Products with zero disruption exposure across fulfillment history
    """

    def analyze(
        self,
        datasets: dict[str, pd.DataFrame],
        supplier_id: str | None = None,
        product_id: str | None = None,
        top_n: int = 10,
        condition: str = "affected",
        entity: str = "product",
    ) -> dict[str, Any]:
        orders = datasets.get("orders_extended")
        if orders is None or orders.empty:
            orders = datasets.get("orders")

        inventory = datasets.get("inventory")
        products = datasets.get("products")
        suppliers = datasets.get("suppliers")

        # -----------------------------------------------------
        # 0. Population Evidence Verification
        # -----------------------------------------------------
        if orders is None or orders.empty:
            return {
                "status": "insufficient_evidence",
                "message": (
                    "Insufficient evidence to determine which products are unaffected. "
                    "The order fulfillment records could not be retrieved from the warehouse datasets."
                ),
                "population_size": 0,
                "affected_count": 0,
                "unaffected_count": 0,
                "findings": [],
                "evidence": [],
            }

        orders_df = orders.copy()

        # Build complete supplier population
        if suppliers is not None and not suppliers.empty and "supplier_id" in suppliers.columns:
            all_supplier_ids = sorted(suppliers["supplier_id"].astype(str).str.upper().unique().tolist())
        else:
            all_supplier_ids = sorted(orders_df["supplier_id"].astype(str).str.upper().unique().tolist())

        # Build complete product population
        if products is not None and not products.empty and "product_id" in products.columns:
            all_product_ids = sorted(products["product_id"].astype(str).str.upper().unique().tolist())
        else:
            all_product_ids = sorted(orders_df["product_id"].astype(str).str.upper().unique().tolist())

        # Supplier names dictionary
        supplier_names = {}
        if suppliers is not None and not suppliers.empty:
            for _, srow in suppliers.iterrows():
                sid = str(srow.get("supplier_id", "")).upper()
                sname = str(srow.get("supplier_name", sid))
                if sid:
                    supplier_names[sid] = sname

        # If evaluating a negative query and complete product population is missing, fail with explicit reason
        norm_cond = str(condition or "affected").strip().lower().replace(" ", "_")
        norm_entity = str(entity or "product").strip().lower()

        if norm_cond in {"not_affected", "unaffected", "no_disruption", "no_disruption_exposure"}:
            if norm_entity == "product" and len(all_product_ids) == 0:
                return {
                    "status": "insufficient_evidence",
                    "message": "Insufficient evidence to determine which products are unaffected: complete product catalog population is missing.",
                    "population_size": 0,
                    "affected_count": 0,
                    "unaffected_count": 0,
                    "findings": [],
                    "evidence": [],
                }
            if norm_entity == "supplier" and len(all_supplier_ids) == 0:
                return {
                    "status": "insufficient_evidence",
                    "message": "Insufficient evidence to determine which suppliers are unaffected: complete supplier population is missing.",
                    "population_size": 0,
                    "affected_count": 0,
                    "unaffected_count": 0,
                    "findings": [],
                    "evidence": [],
                }

        # Filter by entity if specifically requested
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
                "status": "insufficient_evidence",
                "message": f"No operational order records found for the requested entity ({supplier_id or product_id}).",
                "population_size": len(all_product_ids) if norm_entity == "product" else len(all_supplier_ids),
                "affected_count": 0,
                "unaffected_count": 0,
                "findings": [],
                "evidence": [],
            }

        # -----------------------------------------------------
        # 1. Supplier Disruption Metrics
        # -----------------------------------------------------
        sup_aggs = {
            "total_orders": ("order_id", "count"),
            "late_orders": ("late_order", "sum"),
        }
        if "disruption_flag" in orders_df.columns:
            sup_aggs["disruption_rate"] = ("disruption_flag", "mean")
            sup_aggs["disrupted_orders"] = ("disruption_flag", "sum")
        else:
            sup_aggs["disruption_rate"] = ("late_order", lambda x: (x.sum() / max(len(x), 1)) * 0.5)
            sup_aggs["disrupted_orders"] = ("late_order", lambda x: int(x.sum() * 0.5))

        if "delay_days" in orders_df.columns:
            sup_aggs["avg_delay"] = ("delay_days", "mean")
        if "lead_time_days" in orders_df.columns:
            sup_aggs["avg_lead_time"] = ("lead_time_days", "mean")

        sup_perf = orders_df.groupby("supplier_id").agg(**sup_aggs).reset_index()
        sup_perf["supplier_id"] = sup_perf["supplier_id"].astype(str).str.upper()
        sup_perf["late_rate"] = sup_perf["late_orders"] / np.maximum(sup_perf["total_orders"], 1)
        if "avg_delay" not in sup_perf.columns:
            sup_perf["avg_delay"] = 0.0
        if "avg_lead_time" not in sup_perf.columns:
            sup_perf["avg_lead_time"] = 14.0

        sup_perf["supplier_name"] = sup_perf["supplier_id"].map(
            lambda sid: supplier_names.get(sid, sid)
        )

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

        # Determine affected suppliers
        is_affected_sup = (
            (sup_perf["supplier_risk_level"].isin(["CRITICAL", "HIGH"]))
            | (sup_perf["disruption_rate"] >= 0.20)
        )
        affected_supplier_ids = set(sup_perf[is_affected_sup]["supplier_id"].unique())
        unaffected_supplier_ids = set(all_supplier_ids) - affected_supplier_ids

        # -----------------------------------------------------
        # 2. Product-Supplier Disruption Metrics
        # -----------------------------------------------------
        prod_sup_aggs = {
            "prod_orders": ("order_id", "count"),
            "prod_units": ("units", "sum"),
            "prod_late_orders": ("late_order", "sum"),
        }
        if "disruption_flag" in orders_df.columns:
            prod_sup_aggs["prod_disrupted_orders"] = ("disruption_flag", "sum")
        else:
            prod_sup_aggs["prod_disrupted_orders"] = ("late_order", lambda x: int(x.sum() * 0.5))

        prod_sup = orders_df.groupby(["product_id", "supplier_id"]).agg(**prod_sup_aggs).reset_index()
        prod_sup["product_id"] = prod_sup["product_id"].astype(str).str.upper()
        prod_sup["supplier_id"] = prod_sup["supplier_id"].astype(str).str.upper()
        prod_sup["prod_late_rate"] = prod_sup["prod_late_orders"] / np.maximum(prod_sup["prod_orders"], 1)

        merged = prod_sup.merge(sup_perf, on="supplier_id", how="left")

        # -----------------------------------------------------
        # 3. Product Inventory & Demand Metrics
        # -----------------------------------------------------
        inv_by_prod: dict[str, dict[str, Any]] = {}
        if inventory is not None and not inventory.empty:
            inv_col = "inventory_units" if "inventory_units" in inventory.columns else ("inventory_level" if "inventory_level" in inventory.columns else None)
            demand_col = "demand" if "demand" in inventory.columns else None

            if inv_col and "product_id" in inventory.columns:
                inv_df = inventory.copy()
                inv_df["product_id"] = inv_df["product_id"].astype(str).str.upper()
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

        merged["avg_inventory"] = merged["product_id"].map(lambda p: inv_by_prod.get(p, {}).get("avg_inventory", 150.0))
        merged["avg_daily_demand"] = merged["product_id"].map(lambda p: inv_by_prod.get(p, {}).get("avg_daily_demand", 20.0))
        merged["days_of_cover"] = merged["product_id"].map(lambda p: inv_by_prod.get(p, {}).get("days_of_cover", 15.0))
        merged["stockout_rate"] = merged["product_id"].map(lambda p: inv_by_prod.get(p, {}).get("stockout_rate", 0.05))

        # -----------------------------------------------------
        # 4. Exposure Score & Disruption Classification
        # -----------------------------------------------------
        cover_penalty = np.clip((30.0 - merged["days_of_cover"]) / 30.0, 0.0, 1.0)
        merged["exposure_score"] = (
            (merged["disruption_rate"] * 35.0)
            + (merged["late_rate"] * 25.0)
            + (cover_penalty * 25.0)
            + (merged["stockout_rate"] * 15.0)
        ).clip(0.0, 100.0).round(1)

        # Criteria for affected products:
        # A product is affected if it has elevated exposure (exposure_score >= 50.0)
        # OR its supplier is a CRITICAL/HIGH risk supplier (supplier disruption rate >= 20.0%)
        merged["is_affected"] = (
            (merged["exposure_score"] >= 50.0)
            | (merged["supplier_id"].isin(affected_supplier_ids))
        )

        affected_product_ids = set(merged[merged["is_affected"]]["product_id"].unique())
        unaffected_product_ids = set(all_product_ids) - affected_product_ids
        zero_disruption_product_ids = set(
            merged[merged["prod_disrupted_orders"] == 0]["product_id"].unique()
        )

        # -----------------------------------------------------
        # 5. Result Selection based on Entity and Condition
        # -----------------------------------------------------
        is_negative = norm_cond in {"not_affected", "unaffected", "no_disruption", "least_affected"}
        is_zero_disr = norm_cond in {"no_disruption_exposure", "zero_disruption"}

        findings: list[dict[str, Any]] = []
        evidence: list[dict[str, Any]] = []

        if norm_entity == "supplier":
            population_size = len(all_supplier_ids)
            affected_count = len(affected_supplier_ids)
            unaffected_count = len(unaffected_supplier_ids)

            if is_negative:
                subset = sup_perf[sup_perf["supplier_id"].isin(unaffected_supplier_ids)].copy()
                subset = subset.sort_values(by=["supplier_risk_score", "disruption_rate"], ascending=True)
                target_classification = "not_affected"
            else:
                subset = sup_perf[sup_perf["supplier_id"].isin(affected_supplier_ids)].copy()
                subset = subset.sort_values(by=["supplier_risk_score", "disruption_rate"], ascending=False)
                target_classification = "affected"

            top_subset = subset.head(top_n).reset_index(drop=True)

            for idx, row in top_subset.iterrows():
                sid = str(row["supplier_id"])
                sname = str(row.get("supplier_name", sid))
                s_risk = str(row["supplier_risk_level"])
                disp = round(float(row["disruption_rate"]) * 100.0, 1)
                late = round(float(row["late_rate"]) * 100.0, 1)
                score = round(float(row["supplier_risk_score"]), 1)
                orders_cnt = int(row["total_orders"])
                lead_t = round(float(row.get("avg_lead_time", 14.0)), 1)

                if target_classification == "not_affected":
                    reason = (
                        f"Supplier {sid} ({sname}) operates at {s_risk} risk (score: {score:.1f}/100) "
                        f"with a {disp:.1f}% disruption rate and {late:.1f}% late rate across {orders_cnt:,} orders, "
                        f"satisfying delivery stability criteria."
                    )
                else:
                    reason = (
                        f"Supplier {sid} ({sname}) operates at {s_risk} risk (score: {score:.1f}/100) "
                        f"with a {disp:.1f}% disruption rate and {late:.1f}% late rate across {orders_cnt:,} orders."
                    )

                item = {
                    "rank": idx + 1,
                    "supplier_id": sid,
                    "supplier_name": sname,
                    "supplier_risk_level": s_risk,
                    "disruption_rate": disp,
                    "late_rate": late,
                    "lead_time": lead_t,
                    "risk_score": score,
                    "total_orders": orders_cnt,
                    "classification": target_classification,
                    "classification_reason": reason,
                }
                findings.append(item)
                evidence.append({
                    "source_type": "analytics",
                    "source_id": f"supplier_disruption:{sid}",
                    "entity_type": "supplier",
                    "entity_id": sid,
                    "metric": "supplier_disruption_impact",
                    "value": score,
                    "data": item,
                    "explanation": reason,
                    "retrieval_method": "structured",
                    "confidence": 1.0,
                })

        else:
            # Entity == "product"
            population_size = len(all_product_ids)
            affected_count = len(affected_product_ids)
            unaffected_count = len(unaffected_product_ids)

            if is_zero_disr:
                subset = merged[merged["product_id"].isin(zero_disruption_product_ids)].copy()
                subset = subset.sort_values(by="exposure_score", ascending=True)
                target_classification = "no_disruption_exposure"
            elif is_negative:
                subset = merged[merged["product_id"].isin(unaffected_product_ids)].copy()
                subset = subset.sort_values(by="exposure_score", ascending=True)
                target_classification = "not_affected"
            else:
                subset = merged[merged["product_id"].isin(affected_product_ids)].copy()
                subset = subset.sort_values(by="exposure_score", ascending=False)
                target_classification = "affected"

            top_subset = subset.head(top_n).reset_index(drop=True)

            for idx, row in top_subset.iterrows():
                pid = str(row["product_id"])
                sid = str(row["supplier_id"])
                sname = str(row.get("supplier_name", sid))
                s_risk = str(row["supplier_risk_level"])
                disp = round(float(row["disruption_rate"]) * 100.0, 1)
                late = round(float(row["late_rate"]) * 100.0, 1)
                doc = round(float(row["days_of_cover"]), 1)
                stockout = round(float(row["stockout_rate"]) * 100.0, 1)
                score = round(float(row["exposure_score"]), 1)
                lead_t = round(float(row.get("avg_lead_time", 14.0)), 1)
                inv_units = round(float(row["avg_inventory"]), 0)
                dem = round(float(row["avg_daily_demand"]), 1)

                if target_classification == "no_disruption_exposure":
                    reason = (
                        f"Product {pid} (Supplier {sid} - {sname}, {s_risk} risk) has 0 recorded fulfillment disruptions "
                        f"(0.0% disruption rate) across order history with {doc:.1f} days of inventory cover."
                    )
                elif target_classification == "not_affected":
                    reason = (
                        f"Product {pid} (Supplier {sid} - {sname}, {s_risk} risk) maintains a low disruption exposure "
                        f"score ({score:.1f}/100) with a {disp:.1f}% supplier disruption rate, {doc:.1f} days of inventory cover, "
                        f"and {stockout:.1f}% stockout rate, placing it outside the supplier-disruption criteria."
                    )
                else:
                    reason = (
                        f"Product {pid} (Supplier {sid} - {sname}, {s_risk} risk) experiences {disp:.1f}% supplier disruption rate, "
                        f"thin inventory cover ({doc:.1f}d), and {stockout:.1f}% stockout rate (Disruption Exposure: {score:.1f}/100)."
                    )

                item = {
                    "rank": idx + 1,
                    "product_id": pid,
                    "supplier_id": sid,
                    "supplier_name": sname,
                    "supplier_risk_level": s_risk,
                    "disruption_rate": disp,
                    "supplier_late_rate": late,
                    "lead_time": lead_t,
                    "avg_daily_demand": dem,
                    "inventory_units": inv_units,
                    "days_of_cover": doc,
                    "stockout_rate": stockout,
                    "exposure_score": score,
                    "classification": target_classification,
                    "classification_reason": reason,
                }
                findings.append(item)
                evidence.append({
                    "source_type": "analytics",
                    "source_id": f"product_disruption_impact:{pid}",
                    "entity_type": "product",
                    "entity_id": pid,
                    "metric": "supplier_disruption_impact",
                    "value": score,
                    "data": item,
                    "explanation": reason,
                    "retrieval_method": "structured",
                    "confidence": 1.0,
                })

        return {
            "status": "success",
            "entity": norm_entity,
            "condition": condition,
            "population_size": population_size,
            "affected_count": affected_count,
            "unaffected_count": unaffected_count,
            "total_products_evaluated": len(all_product_ids),
            "total_suppliers_evaluated": len(all_supplier_ids),
            "findings": findings,
            "evidence": evidence,
        }
