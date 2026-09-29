from __future__ import annotations

from typing import Any
import pandas as pd


class DeliveryPerformanceAnalyzer:
    """
    Deterministic analytics engine for network-level and segment delivery performance.
    Calculates exact delivery metrics from operational order data:
    - total_orders
    - late_orders
    - on_time_orders
    - late_rate
    - on_time_rate
    - avg_delay_days
    - avg_delay_when_late
    - avg_lead_time_days
    """

    def analyze(
        self,
        orders: pd.DataFrame,
        plan: Any = None,
        mode: str = "performance",
    ) -> pd.DataFrame:
        if orders is None or orders.empty:
            return pd.DataFrame()

        df = orders.copy()

        # Parse late_order
        if "late_order" in df.columns:
            df["late_order"] = pd.to_numeric(
                df["late_order"], errors="coerce"
            ).fillna(0)
        else:
            df["late_order"] = 0

        # Parse delay_days
        delay_col = None
        for col in ["delay_days", "delay", "delivery_delay", "days_late"]:
            if col in df.columns:
                delay_col = col
                df[delay_col] = pd.to_numeric(
                    df[delay_col], errors="coerce"
                ).fillna(0)
                break

        # Parse lead_time_days
        lead_time_col = None
        for col in ["lead_time_days", "lead_time"]:
            if col in df.columns:
                lead_time_col = col
                df[lead_time_col] = pd.to_numeric(
                    df[lead_time_col], errors="coerce"
                ).fillna(0)
                break

        total_orders = len(df)
        late_orders = int(df["late_order"].sum())
        on_time_orders = int(total_orders - late_orders)

        late_rate = float(late_orders / total_orders) if total_orders > 0 else 0.0
        on_time_rate = float(on_time_orders / total_orders) if total_orders > 0 else 0.0

        avg_delay = float(df[delay_col].mean()) if delay_col else 0.0
        late_subset = df[df["late_order"] == 1]
        avg_delay_when_late = (
            float(late_subset[delay_col].mean())
            if delay_col and not late_subset.empty
            else avg_delay
        )
        avg_lead_time = float(df[lead_time_col].mean()) if lead_time_col else 0.0

        network_record = {
            "scope": "network",
            "entity": "delivery",
            "total_orders": total_orders,
            "late_orders": late_orders,
            "on_time_orders": on_time_orders,
            "late_rate": round(late_rate, 4),
            "on_time_rate": round(on_time_rate, 4),
            "avg_delay_days": round(avg_delay, 2),
            "avg_delay_when_late": round(avg_delay_when_late, 2),
            "avg_lead_time_days": round(avg_lead_time, 2),
        }

        # Supplier comparison or per-supplier evaluation:
        comp_entities = []
        if plan:
            if getattr(plan, "comparison", None) and isinstance(plan.comparison, dict):
                comp_entities = [str(e).strip().upper() for e in plan.comparison.get("entities", []) if e]
            elif getattr(plan, "entity_ids", None) and len(plan.entity_ids) >= 2:
                comp_entities = [str(e).strip().upper() for e in plan.entity_ids if e]
        
        if comp_entities and "supplier_id" in df.columns:
            from app.query.scope import normalize_supplier_id
            norm_comps = {normalize_supplier_id(e) for e in comp_entities}
            sids_col = df["supplier_id"].astype(str).str.strip().str.upper()
            norm_sids_col = sids_col.apply(normalize_supplier_id)
            comp_df = df[sids_col.isin(comp_entities) | norm_sids_col.isin(norm_comps)].copy()
            if not comp_df.empty:
                sup_grouped = (
                    comp_df.groupby("supplier_id")
                    .agg(
                        total_orders=("order_id" if "order_id" in comp_df.columns else comp_df.columns[0], "count"),
                        late_orders=("late_order", "sum"),
                        avg_delay_days=(delay_col, "mean") if delay_col else ("late_order", "mean"),
                        avg_lead_time_days=(lead_time_col, "mean") if lead_time_col else ("late_order", "mean"),
                    )
                    .reset_index()
                )
                sup_grouped["on_time_orders"] = sup_grouped["total_orders"] - sup_grouped["late_orders"]
                sup_grouped["late_rate"] = (sup_grouped["late_orders"] / sup_grouped["total_orders"]).round(4)
                sup_grouped["on_time_rate"] = (sup_grouped["on_time_orders"] / sup_grouped["total_orders"]).round(4)
                sup_grouped["avg_delay_days"] = sup_grouped["avg_delay_days"].round(2)
                sup_grouped["avg_lead_time_days"] = sup_grouped["avg_lead_time_days"].round(2)
                sup_grouped["scope"] = "supplier"
                sup_grouped["entity"] = "supplier"
                return sup_grouped

        # If analyzing causes or breakdown ("Why are deliveries delayed?"):
        if mode == "analysis" or (plan and getattr(plan, "metric", None) == "delivery_analysis"):
            records = [network_record]
            # Carrier 3PL contribution
            three_pl_col = None
            for c in ["3pl", "three_pl", "logistics_provider"]:
                if c in df.columns:
                    three_pl_col = c
                    break

            if three_pl_col:
                carrier_grouped = (
                    df.groupby(three_pl_col)
                    .agg(
                        total_orders=("order_id" if "order_id" in df.columns else df.columns[0], "count"),
                        late_orders=("late_order", "sum"),
                        avg_delay_days=(delay_col, "mean") if delay_col else ("late_order", "mean"),
                    )
                    .reset_index()
                )
                carrier_grouped["late_rate"] = (
                    carrier_grouped["late_orders"] / carrier_grouped["total_orders"]
                )
                carrier_top = carrier_grouped.sort_values("late_rate", ascending=False).head(3)
                for _, row in carrier_top.iterrows():
                    records.append({
                        "scope": "carrier",
                        "three_pl": row[three_pl_col],
                        "total_orders": int(row["total_orders"]),
                        "late_orders": int(row["late_orders"]),
                        "late_rate": round(float(row["late_rate"]), 4),
                        "avg_delay_days": round(float(row["avg_delay_days"]), 2),
                        "risk_level": "CRITICAL" if row["late_rate"] > 0.85 else "HIGH",
                    })

            return pd.DataFrame(records)

        return pd.DataFrame([network_record])
