from __future__ import annotations

from typing import Any

import pandas as pd

from app.analytics.product_sales import ProductSalesAnalyzer
from app.analytics.demand_ranking import DemandRankingAnalyzer
from app.analytics.stockout_ranking import StockoutRankingAnalyzer
from app.analytics.inventory_risk import InventoryRiskAnalyzer
from app.analytics.supplier_risk import SupplierRiskAnalyzer
from app.analytics.delivery_risk import DeliveryRiskAnalyzer
from app.analytics.product_cost import ProductCostAnalyzer
from app.analytics.product_supplier import ProductSupplierAnalyzer

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
                "status": "success",
                "findings": [],
                "evidence": [],
                "message": (
                    "No matching supply-chain data was found."
                ),
            }

        dataframe = dataframe.copy()

        # =====================================================
        # FILTER BY EXPLICIT ENTITY
        # =====================================================

        if plan.entity_id and self.entity_column:

            if self.entity_column in dataframe.columns:

                dataframe = dataframe[
                    dataframe[self.entity_column]
                    .astype(str)
                    .str.upper()
                    == str(plan.entity_id).upper()
                ].copy()

        if dataframe.empty:

            return {
                "status": "success",
                "findings": [],
                "evidence": [],
                "message": (
                    f"No data was found for "
                    f"{plan.entity_id}."
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

        if plan.operation == "rank":

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

        evidence = self._build_evidence(
            records=records,
            plan=plan,
        )

        return {
            "status": "success",
            "findings": records,
            "evidence": evidence,
            "message": self._build_message(
                plan=plan,
                records=records,
            ),
        }

    # =========================================================
    # RUN ANALYTICS
    # =========================================================

    def _run_analysis(
        self,
        plan: QueryPlan,
    ) -> pd.DataFrame:

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

            return self.analyzer.analyze(
                inventory=inventory,
                top_n=None,
            )

                # ---------------------------------------------------------
        # Product cost
        # ---------------------------------------------------------

        if isinstance(
            self.analyzer,
            ProductCostAnalyzer,
        ):
            datasets = self._datasets()

            products = datasets.get("products")

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

            product_ids = None
            supplier_ids = None

            if plan.filters:
                product_ids = plan.filters.get("product_ids")
                supplier_ids = plan.filters.get("supplier_ids")

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

            return self.analyzer.analyze(
                top_n=None
            )

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

            return self.analyzer.analyze(
                orders=orders
            )

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

            if pd.isna(value):

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

            evidence.append(
                {
                    "source": (
                        plan.metric
                        or "supply_chain_analytics"
                    ),
                    "metric": plan.metric,
                    "entity": plan.entity,
                    "entity_id": plan.entity_id,
                    "data": record,
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

    return registry
