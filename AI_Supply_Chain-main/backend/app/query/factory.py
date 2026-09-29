from __future__ import annotations

from typing import Any

import pandas as pd

from app.analytics.product_sales import ProductSalesAnalyzer
from app.analytics.demand_ranking import DemandRankingAnalyzer
from app.analytics.stockout_ranking import StockoutRankingAnalyzer
from app.analytics.inventory_risk import InventoryRiskAnalyzer
from app.analytics.supplier_risk import SupplierRiskAnalyzer
from app.analytics.delivery_risk import DeliveryRiskAnalyzer
from app.analytics.delivery_performance import DeliveryPerformanceAnalyzer
from app.analytics.product_cost import ProductCostAnalyzer
from app.analytics.product_supplier import ProductSupplierAnalyzer
from app.analytics.offers_analyzer import OffersAnalyzer
from app.analytics.lead_time_anomaly import LeadTimeAnomalyAnalyzer
from app.analytics.supplier_disruption_impact import SupplierDisruptionImpactAnalyzer
from app.analytics.major_risks import MajorRisksAnalyzer
from app.analytics.forecasting import DemandForecaster
from app.analytics.product_profile import ProductProfileAnalyzer

from app.query.registry import AnalyticsRegistry
from app.query.schema import QueryPlan
from app.services.data_service import DataService


class AnalyticsAdapter:
    """
    Adapter between existing deterministic analytics classes
    and the QueryExecutor.

    Existing analytics return pandas DataFrames.

    QueryExecutor expects:

        {
            "status": "success",
            "findings": [...],
            "evidence": [...]
        }

    This adapter converts analytical results into that format.
    """

    def __init__(
        self,
        analyzer: Any,
        data_service: DataService,
        dataset_name: str | None = None,
        entity_column: str | None = None,
    ):
        self.analyzer = analyzer
        self.data_service = data_service
        self.dataset_name = dataset_name
        self.entity_column = entity_column

    # =========================================================
    # EXECUTION
    # =========================================================

    def execute(
        self,
        plan: QueryPlan,
    ) -> dict[str, Any]:

        dataframe = self._run_analysis(plan)

        if dataframe is None:
            dataframe = pd.DataFrame()

        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError(
                f"Analytics '{plan.metric}' must return "
                "a pandas DataFrame."
            )

        if dataframe.empty:
            return {
                "status": "insufficient_evidence",
                "findings": [],
                "evidence": [],
                "message": (
                    "No matching supply-chain data was found."
                ),
            }

        dataframe = dataframe.copy()

        # =====================================================
        # =====================================================
        # FILTER BY EXPLICIT ENTITY / COMPARISON ENTITIES
        # =====================================================

        comp_entities = []
        if getattr(plan, "comparison", None) and isinstance(plan.comparison, dict):
            comp_entities = [str(e).strip().upper() for e in plan.comparison.get("entities", []) if e]
        elif getattr(plan, "entity_ids", None) and len(plan.entity_ids) >= 2:
            comp_entities = [str(e).strip().upper() for e in plan.entity_ids if e]

        if comp_entities and self.entity_column and self.entity_column in dataframe.columns:
            if self.entity_column == "supplier_id":
                from app.query.scope import normalize_supplier_id
                norm_comps = {normalize_supplier_id(e) for e in comp_entities}
                col_series = dataframe[self.entity_column].astype(str).str.strip().str.upper()
                norm_series = col_series.apply(normalize_supplier_id)
                dataframe = dataframe[
                    col_series.isin(comp_entities) | norm_series.isin(norm_comps)
                ].copy()
            else:
                dataframe = dataframe[
                    dataframe[self.entity_column].astype(str).str.upper().isin(comp_entities)
                ].copy()
        elif plan.entity_id and self.entity_column:

            if self.entity_column in dataframe.columns:

                target_id = str(plan.entity_id).strip().upper()
                if self.entity_column == "supplier_id":
                    from app.query.scope import normalize_supplier_id
                    norm_target = normalize_supplier_id(target_id)
                    col_series = dataframe[self.entity_column].astype(str).str.strip().str.upper()
                    norm_series = col_series.apply(normalize_supplier_id)
                    dataframe = dataframe[
                        (col_series == target_id) | (norm_series == norm_target)
                    ].copy()
                else:
                    dataframe = dataframe[
                        dataframe[self.entity_column]
                        .astype(str)
                        .str.upper()
                        == target_id
                    ].copy()

        # =====================================================
        # FILTER BY THRESHOLD
        # =====================================================

        if getattr(plan, "threshold", None) and isinstance(plan.threshold, dict):
            t_op = str(plan.threshold.get("operator", ">")).strip()
            try:
                t_val = float(plan.threshold.get("value", 0))
            except (ValueError, TypeError):
                t_val = 0.0
            t_unit = str(plan.threshold.get("unit", "")).strip()

            target_col = None
            for cand in [plan.metric, "risk_score", "stockout_rate", "days_of_cover", "late_rate", "inventory_units"]:
                if cand and cand in dataframe.columns:
                    target_col = cand
                    break

            if target_col and target_col in dataframe.columns:
                norm_val = t_val
                # If percentage and column values are in 0.0 - 1.0 range (e.g. stockout_rate, late_rate)
                if t_unit == "%" and norm_val > 1.0:
                    max_in_col = dataframe[target_col].max()
                    if max_in_col <= 1.0:
                        norm_val = norm_val / 100.0

                if t_op in {">", ">="}:
                    dataframe = dataframe[dataframe[target_col] >= norm_val].copy()
                elif t_op in {"<", "<="}:
                    dataframe = dataframe[dataframe[target_col] <= norm_val].copy()

        if dataframe.empty:

            return {
                "status": "insufficient_evidence",
                "findings": [],
                "evidence": [],
                "message": (
                    f"No data was found for "
                    f"{plan.entity_id or 'the specified criteria'}."
                ),
            }

        # =====================================================
        # APPLY SORTING / DIRECTION
        # =====================================================

        dataframe = self._apply_direction(
            dataframe=dataframe,
            plan=plan,
        )

        # =====================================================
        # LIMIT RESULTS
        # =====================================================

        if plan.metric in {"major_risks", "summary", "risk_profile"}:

            pass

        elif plan.operation == "compare" or comp_entities:

            dataframe = dataframe.head(len(comp_entities) if comp_entities else 5)

        elif plan.operation in {"rank", "filter"}:

            dataframe = dataframe.head(5)

        elif plan.operation == "investigate":

            dataframe = dataframe.head(10)

        elif plan.operation == "explain":

            dataframe = dataframe.head(1)

        # =====================================================
        # CONVERT TO JSON-SAFE RECORDS
        # =====================================================

        records = self._records(
            dataframe
        )

        if plan.metric == "major_risks" and getattr(self, "_cached_major_risks_evidence", None):
            evidence = list(self._cached_major_risks_evidence)
        else:
            evidence = self._build_evidence(
                records=records,
                plan=plan,
            )

        resp = {
            "status": "success",
            "findings": records,
            "evidence": evidence,
            "message": self._build_message(
                plan=plan,
                records=records,
            ),
        }
        if hasattr(self, "last_metadata") and self.last_metadata:
            resp.update(self.last_metadata)
        return resp

    # =========================================================
    # RUN ANALYTICS
    # =========================================================

    def _run_analysis(
        self,
        plan: QueryPlan,
    ) -> pd.DataFrame:

        # -----------------------------------------------------
        # Extract scope filters
        # -----------------------------------------------------
        allowed_pids: set[str] | None = None
        allowed_sids: set[str] | None = None
        if plan.filters:
            pids = plan.filters.get("product_ids") or plan.filters.get("authorized_products")
            if pids:
                allowed_pids = {str(p).strip().upper() for p in pids if p is not None}
            sids = plan.filters.get("supplier_ids")
            if sids:
                allowed_sids = {str(s).strip().upper() for s in sids if s is not None}
            elif plan.filters.get("supplier_id"):
                allowed_sids = {str(plan.filters.get("supplier_id")).strip().upper()}

        # =====================================================
        # PRODUCT PROFILE
        # =====================================================

        if isinstance(
            self.analyzer,
            ProductProfileAnalyzer,
        ):
            datasets = self._datasets()
            products = datasets.get("products")
            pid = plan.entity_id or (plan.entity_ids[0] if getattr(plan, "entity_ids", None) else None)
            return self.analyzer.analyze(
                products=products,
                product_id=pid,
                product_ids=plan.entity_ids or ([pid] if pid else None),
            )

        # =====================================================
        # OFFERS
        # =====================================================

        if isinstance(
            self.analyzer,
            OffersAnalyzer,
        ):
            supplier_id = None
            product_id = None
            if plan.entity == "supplier" or (plan.entity_id and str(plan.entity_id).upper().startswith("S")):
                supplier_id = plan.entity_id
            elif plan.entity == "product" or (plan.entity_id and str(plan.entity_id).upper().startswith("P")):
                product_id = plan.entity_id

            if plan.filters:
                if plan.filters.get("supplier_id"):
                    supplier_id = plan.filters.get("supplier_id")
                if plan.filters.get("product_id"):
                    product_id = plan.filters.get("product_id")

            sids_list = list(allowed_sids) if allowed_sids else None
            pids_list = list(allowed_pids) if allowed_pids else None

            return self.analyzer.analyze(
                supplier_id=supplier_id,
                product_id=product_id,
                supplier_ids=sids_list,
                product_ids=pids_list,
                top_n=None,
            )

        # =====================================================
        # PRODUCT SALES
        # =====================================================

        if isinstance(
            self.analyzer,
            ProductSalesAnalyzer,
        ):

            datasets = self._datasets()

            orders = datasets.get(
                "orders_extended"
            )

            if plan.metric == "total_orders" and (
                plan.entity == "supplier"
                or (plan.filters and plan.filters.get("supplier_ids"))
                or (plan.entity_id and str(plan.entity_id).upper().startswith("S"))
            ):
                if orders is None or orders.empty:
                    return pd.DataFrame(
                        columns=["supplier_id", "total_orders"]
                    )

                supplier_orders = orders[["supplier_id"]].copy()
                supplier_orders["supplier_id"] = supplier_orders[
                    "supplier_id"
                ].astype(str).str.upper()
                supplier_orders = supplier_orders.dropna().drop_duplicates()

                if plan.entity_id:
                    supplier_orders = supplier_orders[
                        supplier_orders["supplier_id"]
                        .astype(str)
                        .str.upper()
                        == str(plan.entity_id).upper()
                    ].copy()

                supplier_counts = (
                    orders.groupby("supplier_id", dropna=False)
                    .size()
                    .reset_index(name="total_orders")
                )
                supplier_counts["supplier_id"] = supplier_counts[
                    "supplier_id"
                ].astype(str).str.upper()

                if plan.entity_id:
                    supplier_counts = supplier_counts[
                        supplier_counts["supplier_id"]
                        .astype(str)
                        .str.upper()
                        == str(plan.entity_id).upper()
                    ].copy()

                if plan.filters and plan.filters.get("supplier_ids"):
                    allowed = {
                        str(sid).upper()
                        for sid in plan.filters["supplier_ids"]
                        if sid is not None
                    }
                    if allowed:
                        supplier_counts = supplier_counts[
                            supplier_counts["supplier_id"].isin(allowed)
                        ].copy()

                return supplier_counts[["supplier_id", "total_orders"]].reset_index(drop=True)

            if orders is not None and not orders.empty:
                orders = orders.copy()
                if allowed_sids and "supplier_id" in orders.columns:
                    orders = orders[orders["supplier_id"].astype(str).str.upper().isin(allowed_sids)].copy()
                if allowed_pids and "product_id" in orders.columns:
                    orders = orders[orders["product_id"].astype(str).str.upper().isin(allowed_pids)].copy()

            if orders is None or orders.empty:
                return pd.DataFrame(
                    columns=[
                        "product_id",
                        "total_sales",
                        "total_units",
                        "order_count",
                        "average_order_value",
                    ]
                )

            result = self.analyzer.analyze(
                orders=orders,
                top_n=None,
            )

            if plan.metric == "total_orders":
                if "order_count" in result.columns:
                    result = result.rename(
                        columns={
                            "order_count": "total_orders"
                        }
                    )

            if plan.metric == "total_units":
                if "total_units" in result.columns:
                    result = result.copy()

            return result

        # =====================================================
        # DEMAND
        # =====================================================

        if isinstance(
            self.analyzer,
            DemandRankingAnalyzer,
        ):

            datasets = self._datasets()

            demand = datasets.get(
                "demand"
            )

            if demand is not None and not demand.empty and allowed_pids:
                demand = demand[
                    demand["product_id"].astype(str).str.upper().isin(allowed_pids)
                ].copy()

            return self.analyzer.analyze(
                demand=demand,
                top_n=None,
            )

        # =====================================================
        # STOCKOUT
        # =====================================================

        if isinstance(
            self.analyzer,
            StockoutRankingAnalyzer,
        ):

            datasets = self._datasets()

            inventory = datasets.get(
                "inventory"
            )

            if inventory is not None and not inventory.empty and allowed_pids:
                inventory = inventory[
                    inventory["product_id"].astype(str).str.upper().isin(allowed_pids)
                ].copy()

            res = self.analyzer.analyze(
                inventory=inventory,
                top_n=None,
            )
            cond = getattr(plan, "condition", None)
            is_low = (
                getattr(plan, "negative_condition", False)
                or cond == "low_risk"
                or getattr(plan, "direction", "none") == "ascending"
            )
            if is_low:
                res = res.sort_values(by="stockout_rate", ascending=True)
            return res

                # ---------------------------------------------------------
        # Product cost
        # ---------------------------------------------------------

        if isinstance(
            self.analyzer,
            ProductCostAnalyzer,
        ):
            datasets = self._datasets()

            products = datasets.get("products")

            if products is not None and not products.empty:
                products = products.copy()
                if allowed_sids and "supplier_id" in products.columns:
                    products = products[
                        products["supplier_id"].astype(str).str.upper().isin(allowed_sids)
                    ].copy()
                if allowed_pids and "product_id" in products.columns:
                    products = products[
                        products["product_id"].astype(str).str.upper().isin(allowed_pids)
                    ].copy()

            return self.analyzer.analyze(
                products=products,
                top_n=None,
            )

        # =====================================================
        # PRODUCT TO SUPPLIER
        # =====================================================

        if isinstance(
            self.analyzer,
            ProductSupplierAnalyzer,
        ):
            datasets = self._datasets()

            products = datasets.get("products")
            suppliers = datasets.get("suppliers")

            product_ids = list(allowed_pids) if allowed_pids else None
            supplier_ids = list(allowed_sids) if allowed_sids else None

            if plan.entity == "supplier" and plan.entity_id:
                supplier_ids = [str(plan.entity_id).upper()]
            elif plan.entity == "product" and plan.entity_id:
                product_ids = [str(plan.entity_id).upper()]

            return self.analyzer.analyze(
                products=products,
                suppliers=suppliers,
                product_ids=product_ids,
                supplier_ids=supplier_ids,
                top_n=None,
            )

        # =====================================================
        # INVENTORY RISK
        # =====================================================

        if isinstance(
            self.analyzer,
            InventoryRiskAnalyzer,
        ):

            result = self.analyzer.analyze(
                top_n=None
            )
            if result is not None and not result.empty and allowed_pids and "product_id" in result.columns:
                result = result[
                    result["product_id"].astype(str).str.upper().isin(allowed_pids)
                ].copy()
            cond = getattr(plan, "condition", None)
            is_low = (
                getattr(plan, "negative_condition", False)
                or cond == "low_risk"
                or getattr(plan, "direction", "none") == "ascending"
            )
            if is_low:
                if plan.operation == "filter":
                    result = result[result["risk_level"].isin(["LOW", "MEDIUM"])].sort_values(by="risk_score", ascending=True)
                else:
                    result = result.sort_values(by="risk_score", ascending=True)
            elif cond == "high_risk" and plan.operation == "filter":
                result = result[result["risk_level"].isin(["CRITICAL", "HIGH"])].sort_values(by="risk_score", ascending=False)
            return result

        # =====================================================
        # SUPPLIER RISK
        # =====================================================

        if isinstance(
            self.analyzer,
            SupplierRiskAnalyzer,
        ):

            datasets = self._datasets()

            orders = datasets.get(
                "orders_extended"
            )

            if orders is not None and not orders.empty and allowed_sids:
                from app.query.scope import normalize_supplier_id
                norm_allowed = {normalize_supplier_id(s) for s in allowed_sids if s}
                sids_col = orders["supplier_id"].astype(str).str.strip().str.upper()
                norm_sids_col = sids_col.apply(normalize_supplier_id)
                orders = orders[
                    sids_col.isin(allowed_sids) | norm_sids_col.isin(norm_allowed)
                ].copy()

            res_df = self.analyzer.analyze(
                orders=orders
            )
            cond = getattr(plan, "condition", None)
            if cond == "not_high_risk":
                res_df = res_df[~res_df["risk_level"].isin(["CRITICAL", "HIGH"])].sort_values(by="late_rate", ascending=True)
            elif cond == "low_risk" or getattr(plan, "negative_condition", False):
                if plan.operation == "filter" and not plan.entity_id:
                    res_df = res_df[res_df["risk_level"].isin(["LOW", "MEDIUM"])].sort_values(by="late_rate", ascending=True)
                elif plan.direction == "ascending":
                    res_df = res_df.sort_values(by="late_rate", ascending=True)
            elif cond == "high_risk":
                if plan.operation == "filter" and not plan.entity_id:
                    res_df = res_df[res_df["risk_level"].isin(["CRITICAL", "HIGH"])].sort_values(by="late_rate", ascending=False)
            return res_df

        # =====================================================
        # DELIVERY RISK
        # =====================================================

        if isinstance(
            self.analyzer,
            DeliveryRiskAnalyzer,
        ):

            datasets = self._datasets()

            orders = datasets.get(
                "orders_extended"
            )

            return self.analyzer.analyze(
                orders=orders
            )

        # =====================================================
        # DELIVERY PERFORMANCE
        # =====================================================

        if isinstance(
            self.analyzer,
            DeliveryPerformanceAnalyzer,
        ):

            datasets = self._datasets()

            orders = datasets.get(
                "orders_extended"
            )
            if orders is None or orders.empty:
                orders = datasets.get("orders")

            if orders is not None and not orders.empty and allowed_sids:
                from app.query.scope import normalize_supplier_id
                norm_allowed = {normalize_supplier_id(s) for s in allowed_sids if s}
                sids_col = orders["supplier_id"].astype(str).str.strip().str.upper()
                norm_sids_col = sids_col.apply(normalize_supplier_id)
                orders = orders[
                    sids_col.isin(allowed_sids) | norm_sids_col.isin(norm_allowed)
                ].copy()

            return self.analyzer.analyze(
                orders=orders,
                plan=plan,
                mode="analysis" if getattr(plan, "metric", None) == "delivery_analysis" else "performance",
            )

        # =====================================================
        # PRODUCT COST
        # =====================================================

        if isinstance(
            self.analyzer,
            ProductCostAnalyzer,
        ):

            datasets = self._datasets()

            products = datasets.get(
                "products"
            )

            return self.analyzer.analyze(
                products=products,
                top_n=None,
            )

        # =====================================================
        # LEAD TIME ANOMALY
        # =====================================================

        if isinstance(
            self.analyzer,
            LeadTimeAnomalyAnalyzer,
        ):
            datasets = self._datasets()
            orders = datasets.get("orders_extended")
            sid = str(plan.entity_id) if plan.entity == "supplier" and plan.entity_id else None
            is_largest = "largest" in getattr(plan, "original_query", "").lower() or (getattr(plan, "operation", None) == "rank" and getattr(plan, "trend", None) == "increase")
            top_n = 1 if is_largest else 15
            res = self.analyzer.analyze(
                orders=orders,
                supplier_id=sid,
                top_n=top_n,
                trend=getattr(plan, "trend", None),
                operation=plan.operation,
                direction=plan.direction,
            )
            return pd.DataFrame(res.get("findings", []))

        # =====================================================
        # SUPPLIER DISRUPTION IMPACT
        # =====================================================

        if isinstance(
            self.analyzer,
            SupplierDisruptionImpactAnalyzer,
        ):
            datasets = self._datasets()
            sid = str(plan.entity_id) if plan.entity == "supplier" and plan.entity_id else None
            pid = str(plan.entity_id) if plan.entity == "product" and plan.entity_id else None
            res = self.analyzer.analyze(
                datasets=datasets,
                supplier_id=sid,
                product_id=pid,
                condition=getattr(plan, "condition", None),
                entity=plan.entity,
            )
            self.last_metadata = {
                "population_size": res.get("population_size"),
                "affected_count": res.get("affected_count"),
                "unaffected_count": res.get("unaffected_count"),
                "condition": res.get("condition"),
                "entity": res.get("entity"),
            }
            return pd.DataFrame(res.get("findings", []))

        # =====================================================
        # MAJOR RISKS
        # =====================================================

        if isinstance(
            self.analyzer,
            MajorRisksAnalyzer,
        ):
            datasets = self._datasets()
            cond = getattr(plan, "condition", "major") or "major"
            neg = getattr(plan, "negative_condition", False)
            res = self.analyzer.analyze(datasets=datasets, condition=cond, negative_condition=neg)
            findings = []
            for domain, data in res.get("findings", {}).items():
                if isinstance(data, dict):
                    findings.append({"risk_domain": domain, "condition": cond, **data})
            self._cached_major_risks_evidence = res.get("evidence", [])
            return pd.DataFrame(findings)

        # =====================================================
        # DEMAND FORECASTING
        # =====================================================

        if isinstance(
            self.analyzer,
            DemandForecaster,
        ):
            datasets = self._datasets()
            orders = datasets.get("orders_extended")
            if orders is None or orders.empty:
                orders = datasets.get("orders")

            pid = str(plan.entity_id or "P00003").strip().upper()
            res = self.analyzer.forecast_product(orders, product_id=pid, horizon=7)
            if res.get("status") == "success":
                rows = []
                avg = res.get("average_recent_demand", 0.0)
                slope = res.get("trend_per_day", 0.0)
                tot_pred = sum(item.get("predicted_demand", 0.0) for item in res.get("forecast", []))
                trend_dir = "increasing" if slope > 0.05 else ("decreasing" if slope < -0.05 else "stable")
                for item in res.get("forecast", []):
                    rows.append({
                        "product_id": pid,
                        "date": item.get("date"),
                        "predicted_demand": item.get("predicted_demand"),
                        "total_forecast_demand": round(tot_pred, 1),
                        "average_recent_demand": round(avg, 2),
                        "trend_per_day": round(slope, 3),
                        "trend_direction": trend_dir,
                    })
                return pd.DataFrame(rows)
            return pd.DataFrame()

        raise TypeError(
            "Unsupported analytics analyzer: "
            f"{type(self.analyzer).__name__}"
        )

    # =========================================================
    # LOAD DATA
    # =========================================================

    def _datasets(
        self,
    ) -> dict[str, pd.DataFrame]:

        result = self.data_service.load_data()

        return result.get(
            "datasets",
            {},
        )

    # =========================================================
    # APPLY DIRECTION
    # =========================================================

    @staticmethod
    def _apply_direction(
        dataframe: pd.DataFrame,
        plan: QueryPlan,
    ) -> pd.DataFrame:

        if plan.direction == "none":

            return dataframe.reset_index(
                drop=True
            )

        if plan.metric == "supplier_disruption_impact" and getattr(plan, "condition", None) in {
            "not_affected", "unaffected", "no_disruption", "no_disruption_exposure", "least_affected"
        }:
            return dataframe.reset_index(drop=True)

        if (
            plan.metric in {"late_rate", "supplier_delivery_risk"}
            and getattr(plan, "condition", None) == "low_risk"
            and plan.direction != "descending"
        ):
            return dataframe.sort_values(by="late_rate", ascending=True).reset_index(drop=True)

        metric = plan.metric

        # -----------------------------------------------------
        # Semantic metric -> actual DataFrame column
        # -----------------------------------------------------

        column_map = {

            # Product
            "total_sales": "total_sales",
            "unit_cost": "unit_cost",

            # Demand
            "total_demand": "total_demand",
            "average_daily_demand": (
                "average_daily_demand"
            ),

            # Inventory
            "stockout_rate": "stockout_rate",
            "risk_score": "risk_score",
            "inventory_units": "avg_inventory",
            "days_of_cover": "days_of_cover",

            # Supplier
            "late_rate": "late_rate",

            # Delivery
            "delivery_delay": "avg_delay_days",
            "delay_days": "avg_delay_days",

            # Forecast / anomaly if later registered
            "lead_time_days": "lead_time_days",
            "lead_time_anomaly": "absolute_change_days",
            "supplier_disruption_impact": "exposure_score",
            "major_risks": "risk_score",
        }

        column = column_map.get(
            metric
        )

        if (
            column
            and column in dataframe.columns
        ):

            ascending = (
                plan.direction
                == "ascending"
            )

            return (
                dataframe
                .sort_values(
                    by=column,
                    ascending=ascending,
                )
                .reset_index(
                    drop=True
                )
            )

        return dataframe.reset_index(
            drop=True
        )

    # =========================================================
    # DATAFRAME -> RECORDS
    # =========================================================

    @staticmethod
    def _records(
        dataframe: pd.DataFrame,
    ) -> list[dict[str, Any]]:

        records = dataframe.to_dict(
            orient="records"
        )

        return [
            AnalyticsAdapter._clean_record(
                record
            )
            for record in records
        ]

    # =========================================================
    # CLEAN NUMPY / PANDAS VALUES
    # =========================================================

    @staticmethod
    def _clean_record(
        record: dict[str, Any],
    ) -> dict[str, Any]:

        cleaned: dict[str, Any] = {}

        for key, value in record.items():

            if isinstance(value, (list, dict, tuple, set)):

                cleaned[key] = value

            elif pd.isna(value):

                cleaned[key] = None

            elif hasattr(
                value,
                "item",
            ):

                cleaned[key] = value.item()

            else:

                cleaned[key] = value

        return cleaned

    # =========================================================
    # BUILD EVIDENCE
    # =========================================================

    @staticmethod
    def _build_evidence(
        records: list[dict[str, Any]],
        plan: QueryPlan,
    ) -> list[dict[str, Any]]:

        evidence: list[dict[str, Any]] = []

        for record in records[:5]:
            metric = plan.metric or "supply_chain_analytics"
            val: Any = None
            explanation = ""

            if metric == "total_demand":
                pid = record.get("product_id") or plan.entity_id
                dem = record.get("total_demand", 0.0)
                val = round(float(dem), 1) if isinstance(dem, (int, float)) else dem
                explanation = f"Product {pid}: total demand of {val:,.1f} units over analyzed period."
            elif metric == "total_sales":
                pid = record.get("product_id") or plan.entity_id
                sales = record.get("total_sales", 0.0)
                val = round(float(sales), 2) if isinstance(sales, (int, float)) else sales
                explanation = f"Product {pid}: total sales volume of ${val:,.2f}."
            elif metric == "unit_cost":
                pid = record.get("product_id") or plan.entity_id
                cost = record.get("unit_cost", 0.0)
                val = round(float(cost), 2) if isinstance(cost, (int, float)) else cost
                explanation = f"Product {pid}: standard unit cost of ${val:,.2f}."
            elif metric == "product_supplier":
                pid = record.get("product_id") or plan.entity_id
                sid = record.get("supplier_id")
                sname = record.get("supplier_name", sid)
                val = f"{sid} ({sname})"
                explanation = f"Product {pid} is supplied by {sid} ({sname})."
            elif metric == "supplier_product":
                sid = record.get("supplier_id") or plan.entity_id
                pid = record.get("product_id")
                val = pid
                explanation = f"Supplier {sid} supplies product {pid}."
            elif metric == "supplier_offers":
                sid = record.get("supplier_id")
                pid = record.get("product_id")
                price = record.get("unit_price", 0.0)
                lead = record.get("lead_time_days", 0)
                val = round(float(price), 2)
                explanation = f"Supplier {sid} offers {pid} at ${price:.2f} with {lead}d lead time."
            elif metric in {"delivery_performance", "delivery_analysis"}:
                tot = record.get("total_orders", 0)
                late = record.get("late_orders", 0)
                on_time = record.get("on_time_orders", tot - late)
                lr = record.get("late_rate", 0.0)
                otr = record.get("on_time_rate", 0.0)
                delay = record.get("avg_delay_days", 0.0)
                avg_late_delay = record.get("avg_delay_when_late", delay)
                three_pl = record.get("three_pl")
                val = round(float(lr) * 100, 2) if isinstance(lr, (int, float)) else lr
                if three_pl:
                    explanation = f"Carrier {three_pl}: {val:.2f}% late rate across {tot:,} orders, average delay {delay:.2f}d."
                else:
                    explanation = (
                        f"Network delivery performance: {otr*100:.2f}% on-time rate ({on_time:,} orders), "
                        f"{val:.2f}% late rate ({late:,} late orders out of {tot:,} total), "
                        f"average delay {delay:.2f}d (average delay when late: {avg_late_delay:.2f}d)."
                    )
            elif metric in {"late_rate", "supplier_delivery_risk"}:
                sid = record.get("supplier_id") or plan.entity_id
                lr = record.get("late_rate", 0.0)
                delay = record.get("avg_delay") or record.get("avg_delay_days", 0.0)
                orders = record.get("total_orders", 0)
                lvl = record.get("risk_level", "EVALUATED")
                val = round(float(lr) * 100, 1) if isinstance(lr, (int, float)) else lr
                explanation = f"Supplier {sid}: {val:.1f}% late rate, average delay {delay:.1f}d across {orders:,} orders ({lvl} risk)."
            elif metric in {"risk_score", "inventory_risk"}:
                pid = record.get("product_id") or plan.entity_id
                score = record.get("risk_score", 0.0)
                stockout = record.get("stockout_rate", 0.0)
                doc = record.get("days_of_cover", 0.0)
                lvl = record.get("risk_level", "EVALUATED")
                val = round(float(score), 1) if isinstance(score, (int, float)) else score
                explanation = f"Product {pid}: risk score {val}, stockout rate {stockout*100:.1f}%, days of cover {doc:.1f}d ({lvl} risk)."
            elif metric == "stockout_rate":
                pid = record.get("product_id") or plan.entity_id
                rate = record.get("stockout_rate", 0.0)
                zero_days = record.get("zero_inventory_days", 0)
                total_days = record.get("total_days", 0)
                avg_inv = record.get("average_inventory", 0.0)
                val = round(float(rate) * 100, 2) if isinstance(rate, (int, float)) else rate
                explanation = f"Product {pid}: {val:.2f}% stockout rate ({zero_days} zero-inventory days out of {total_days} total days, average inventory: {avg_inv:.1f} units)."
            elif metric in {"inventory_units", "product_inventory"}:
                pid = record.get("product_id") or plan.entity_id
                inv = record.get("inventory_units") or record.get("avg_inventory") or record.get("min_inventory", 0.0)
                doc = record.get("days_of_cover", 0.0)
                val = round(float(inv), 1) if isinstance(inv, (int, float)) else inv
                explanation = f"Product {pid}: recorded inventory {val} units, days of cover {doc:.1f}d."
            elif metric in {"forecast_demand", "forecast"}:
                pid = record.get("product_id") or plan.entity_id
                pred = record.get("total_forecast_demand") or record.get("predicted_demand", 0.0)
                avg = record.get("average_recent_demand", 0.0)
                val = pred
                explanation = f"Product {pid} demand forecast: 7-day projected demand of {pred:.1f} units (recent average: {avg:.2f} units/day)."
            elif metric == "lead_time_anomaly":
                sid = record.get("supplier_id") or plan.entity_id
                diff = record.get("absolute_change_days", 0.0)
                pct = record.get("percentage_change", 0.0)
                status = record.get("status", "Anomalous")
                val = round(float(diff), 1) if isinstance(diff, (int, float)) else diff
                explanation = f"Supplier {sid}: lead time change {diff:+.1f}d ({pct:+.1f}%), status: {status}."
            elif metric == "supplier_disruption_impact":
                pid = record.get("product_id") or plan.entity_id
                sid = record.get("supplier_id")
                score = record.get("exposure_score") if record.get("exposure_score") is not None else record.get("disruption_exposure_score", 0.0)
                val = round(float(score), 1) if isinstance(score, (int, float)) else score
                if record.get("classification_reason"):
                    explanation = str(record["classification_reason"])
                else:
                    classification = record.get("classification", "evaluated")
                    explanation = f"Product {pid} (Supplier {sid}): disruption exposure score {val}/100 ({classification})."
            elif metric == "major_risks":
                domain = record.get("risk_domain", "risk_domain")
                val = domain
                if domain == "supplier_risk":
                    crit = record.get("critical_count", 0)
                    high = record.get("high_count", 0)
                    explanation = f"Supplier delivery risk: {crit:.0f} Critical and {high:.0f} High risk suppliers identified."
                elif domain == "inventory_risk":
                    stockouts = record.get("products_with_stockouts", 0)
                    explanation = f"Inventory vulnerability: {stockouts:.0f} products face historical stockout exposure."
                elif domain == "delivery_risk":
                    late = record.get("system_late_rate", 0.0)
                    delay = record.get("system_avg_delay", 0.0)
                    explanation = f"Logistics carrier friction: system late rate {late:.1f}%, average delay {delay:.1f}d."
                elif domain == "route_risk":
                    rt_cnt = record.get("routes_evaluated", 0)
                    explanation = f"Transportation routes: {rt_cnt:.0f} active shipping routes evaluated."
                elif domain == "lead_time_anomalies":
                    anom = record.get("anomalies_detected", 0)
                    explanation = f"Lead time inflation: {anom:.0f} suppliers detected with significant lead-time surges."
                else:
                    explanation = f"Major risk domain: {domain}."
            else:
                val = record.get(metric) or record.get("value")
                summary_parts = [f"{k}: {v}" for k, v in record.items() if not isinstance(v, (dict, list)) and v is not None][:3]
                ent = plan.entity_id or record.get("product_id") or record.get("supplier_id") or ""
                explanation = f"{metric.replace('_', ' ').title()}{(' for ' + str(ent)) if ent else ''}: {', '.join(summary_parts)}." if summary_parts else f"Structured finding for {metric}."

            evidence.append(
                {
                    "source": metric,
                    "metric": metric,
                    "entity": plan.entity,
                    "entity_id": plan.entity_id,
                    "value": val,
                    "explanation": explanation,
                    "data": record,
                    "retrieval_method": "structured",
                    "confidence": 1.0,
                }
            )

        return evidence

    # =========================================================
    # BUILD EXECUTION MESSAGE
    # =========================================================

    @staticmethod
    def _build_message(
        plan: QueryPlan,
        records: list[dict[str, Any]],
    ) -> str:

        if not records:

            return (
                "No matching supply-chain "
                "data was found."
            )

        if plan.operation == "rank":

            if plan.direction == "ascending":

                return (
                    "Ranking completed from "
                    "lowest to highest."
                )

            return (
                "Ranking completed from "
                "highest to lowest."
            )

        if plan.operation == "explain":

            return (
                "The requested supply-chain "
                "risk evidence was identified."
            )

        return (
            "Supply-chain analysis completed "
            "using the underlying analytical data."
        )


# =============================================================
# ANALYTICS REGISTRY FACTORY
# =============================================================

def create_analytics_registry(
    data_service: DataService | None = None,
) -> AnalyticsRegistry:
    """
    Create the central deterministic analytics registry.

    The registry maps semantic metrics to analytical
    implementations.

    The LLM understands the user's question.

    The deterministic analytics engine calculates
    the actual business metrics.
    """

    if data_service is None:

        data_service = DataService()

    registry = AnalyticsRegistry()

    # =========================================================
    # PRODUCT SALES
    # =========================================================

    registry.register(
        "total_sales",
        AnalyticsAdapter(
            analyzer=ProductSalesAnalyzer(),
            data_service=data_service,
            dataset_name="orders_extended",
            entity_column="product_id",
        ),
    )

    registry.register(
        "total_orders",
        AnalyticsAdapter(
            analyzer=ProductSalesAnalyzer(),
            data_service=data_service,
            dataset_name="orders_extended",
            entity_column="product_id",
        ),
    )

    registry.register(
        "total_units",
        AnalyticsAdapter(
            analyzer=ProductSalesAnalyzer(),
            data_service=data_service,
            dataset_name="orders_extended",
            entity_column="product_id",
        ),
    )

    # =========================================================
    # PRODUCT COST
    # =========================================================

    registry.register(
        "unit_cost",
        AnalyticsAdapter(
            analyzer=ProductCostAnalyzer(),
            data_service=data_service,
            dataset_name="product_attributes",
            entity_column="product_id",
        ),
    )

    registry.register(
        "product_profile",
        AnalyticsAdapter(
            analyzer=ProductProfileAnalyzer(data_service),
            data_service=data_service,
            dataset_name="products",
            entity_column="product_id",
        ),
    )

    registry.register(
        "product_details",
        AnalyticsAdapter(
            analyzer=ProductProfileAnalyzer(data_service),
            data_service=data_service,
            dataset_name="products",
            entity_column="product_id",
        ),
    )

    # =========================================================
    # DEMAND
    # =========================================================

    registry.register(
        "total_demand",
        AnalyticsAdapter(
            analyzer=DemandRankingAnalyzer(),
            data_service=data_service,
            dataset_name="demand",
            entity_column="product_id",
        ),
    )

    registry.register(
        "average_daily_demand",
        AnalyticsAdapter(
            analyzer=DemandRankingAnalyzer(),
            data_service=data_service,
            dataset_name="demand",
            entity_column="product_id",
        ),
    )

    # =========================================================
    # STOCKOUT
    # =========================================================

    registry.register(
        "stockout_rate",
        AnalyticsAdapter(
            analyzer=StockoutRankingAnalyzer(),
            data_service=data_service,
            dataset_name="inventory",
            entity_column="product_id",
        ),
    )

    # =========================================================
    # INVENTORY RISK
    # =========================================================

    registry.register(
        "risk_score",
        AnalyticsAdapter(
            analyzer=InventoryRiskAnalyzer(
                data_service=data_service
            ),
            data_service=data_service,
            dataset_name="inventory",
            entity_column="product_id",
        ),
    )

    registry.register(
        "days_of_cover",
        AnalyticsAdapter(
            analyzer=InventoryRiskAnalyzer(
                data_service=data_service
            ),
            data_service=data_service,
            dataset_name="inventory",
            entity_column="product_id",
        ),
    )

    registry.register(
        "inventory_units",
        AnalyticsAdapter(
            analyzer=InventoryRiskAnalyzer(
                data_service=data_service
            ),
            data_service=data_service,
            dataset_name="inventory",
            entity_column="product_id",
        ),
    )

    # =========================================================
    # SUPPLIER
    # =========================================================

    registry.register(
        "late_rate",
        AnalyticsAdapter(
            analyzer=SupplierRiskAnalyzer(),
            data_service=data_service,
            dataset_name="orders_extended",
            entity_column="supplier_id",
        ),
    )

    registry.register(
        "product_supplier",
        AnalyticsAdapter(
            analyzer=ProductSupplierAnalyzer(),
            data_service=data_service,
            dataset_name="products",
            entity_column="product_id",
        ),
    )

    registry.register(
        "supplier_product",
        AnalyticsAdapter(
            analyzer=ProductSupplierAnalyzer(),
            data_service=data_service,
            dataset_name="products",
            entity_column="supplier_id",
        ),
    )

    # =========================================================
    # DELIVERY
    # =========================================================

    registry.register(
        "delivery_delay",
        AnalyticsAdapter(
            analyzer=DeliveryRiskAnalyzer(),
            data_service=data_service,
            dataset_name="orders_extended",
            entity_column="three_pl",
        ),
    )

    registry.register(
        "delay_days",
        AnalyticsAdapter(
            analyzer=DeliveryRiskAnalyzer(),
            data_service=data_service,
            dataset_name="orders_extended",
            entity_column="three_pl",
        ),
    )

    registry.register(
        "delivery_performance",
        AnalyticsAdapter(
            analyzer=DeliveryPerformanceAnalyzer(),
            data_service=data_service,
            dataset_name="orders_extended",
            entity_column=None,
        ),
    )

    registry.register(
        "delivery_analysis",
        AnalyticsAdapter(
            analyzer=DeliveryPerformanceAnalyzer(),
            data_service=data_service,
            dataset_name="orders_extended",
            entity_column=None,
        ),
    )

    registry.register(
        "on_time_rate",
        AnalyticsAdapter(
            analyzer=DeliveryPerformanceAnalyzer(),
            data_service=data_service,
            dataset_name="orders_extended",
            entity_column=None,
        ),
    )

    registry.register(
        "late_orders",
        AnalyticsAdapter(
            analyzer=DeliveryPerformanceAnalyzer(),
            data_service=data_service,
            dataset_name="orders_extended",
            entity_column=None,
        ),
    )

    # =========================================================
    # OFFERS
    # =========================================================

    registry.register(
        "supplier_offers",
        AnalyticsAdapter(
            analyzer=OffersAnalyzer(),
            data_service=data_service,
            dataset_name="supplier_offers",
            entity_column="supplier_id",
        ),
    )

    registry.register(
        "offers",
        AnalyticsAdapter(
            analyzer=OffersAnalyzer(),
            data_service=data_service,
            dataset_name="supplier_offers",
            entity_column="supplier_id",
        ),
    )

    # =========================================================
    # DOMAIN SPECIFIC ANALYTICS
    # =========================================================

    registry.register(
        "lead_time_anomaly",
        AnalyticsAdapter(
            analyzer=LeadTimeAnomalyAnalyzer(),
            data_service=data_service,
            dataset_name="orders_extended",
            entity_column="supplier_id",
        ),
    )

    registry.register(
        "supplier_disruption_impact",
        AnalyticsAdapter(
            analyzer=SupplierDisruptionImpactAnalyzer(),
            data_service=data_service,
            dataset_name="orders_extended",
            entity_column="product_id",
        ),
    )

    registry.register(
        "major_risks",
        AnalyticsAdapter(
            analyzer=MajorRisksAnalyzer(),
            data_service=data_service,
            dataset_name="orders_extended",
            entity_column=None,
        ),
    )

    registry.register(
        "supplier_investigation",
        AnalyticsAdapter(
            analyzer=SupplierRiskAnalyzer(),
            data_service=data_service,
            dataset_name="orders_extended",
            entity_column="supplier_id",
        ),
    )

    registry.register(
        "forecast_demand",
        AnalyticsAdapter(
            analyzer=DemandForecaster(),
            data_service=data_service,
            dataset_name="orders_extended",
            entity_column="product_id",
        ),
    )

    registry.register(
        "forecast",
        AnalyticsAdapter(
            analyzer=DemandForecaster(),
            data_service=data_service,
            dataset_name="orders_extended",
            entity_column="product_id",
        ),
    )

    return registry
