from __future__ import annotations

import pandas as pd

from app.services.data_service import DataService
from app.analytics.supplier_risk import SupplierRiskAnalyzer
from app.analytics.delivery_risk import DeliveryRiskAnalyzer
from app.analytics.inventory_risk import InventoryRiskAnalyzer


class EvidenceService:

    def __init__(self):

        self.data_service = DataService()

        self.supplier_analyzer = SupplierRiskAnalyzer()

        self.delivery_analyzer = DeliveryRiskAnalyzer()

        # IMPORTANT:
        # InventoryRiskAnalyzer now needs DataService
        self.inventory_analyzer = InventoryRiskAnalyzer(
            self.data_service
        )

    # =============================================================
    # LOAD DATA
    # =============================================================

    def _load(self):

        result = self.data_service.load_data()

        if not isinstance(result, dict):

            raise ValueError(
                "DataService.load_data() must return a dictionary."
            )

        if "datasets" not in result:

            raise ValueError(
                "DataService.load_data() did not return a 'datasets' object."
            )

        return result

    # =============================================================
    # SUPPLIER EVIDENCE
    # =============================================================

    def supplier_evidence(
        self,
        supplier_id: str
    ) -> dict:

        result = self._load()

        datasets = result["datasets"]

        orders = datasets.get("order_features")

        if orders is None:

            return {
                "status": "error",
                "message": (
                    "order_features dataset is not available."
                )
            }

        supplier_col = self._find_column(
            orders,
            [
                "supplier_id",
                "supplier",
                "supplierid"
            ]
        )

        if supplier_col is None:

            return {
                "status": "error",
                "message": (
                    "Supplier information is not available "
                    "in order data."
                )
            }

        supplier_orders = orders[
            orders[supplier_col].astype(str)
            == str(supplier_id)
        ].copy()

        if supplier_orders.empty:

            return {
                "status": "not_found",
                "supplier_id": supplier_id,
                "message": (
                    f"No order evidence found for "
                    f"supplier {supplier_id}."
                )
            }

        risk_df = self.supplier_analyzer.analyze(
            orders
        )

        risk_row = risk_df[
            risk_df["supplier_id"].astype(str)
            == str(supplier_id)
        ]

        risk = {}

        if not risk_row.empty:

            risk = risk_row.iloc[0].to_dict()

        total_orders = len(supplier_orders)

        late_orders = 0

        late_col = self._find_column(
            supplier_orders,
            [
                "late_order",
                "late",
                "is_late"
            ]
        )

        if late_col:

            late_orders = int(
                pd.to_numeric(
                    supplier_orders[late_col],
                    errors="coerce"
                )
                .fillna(0)
                .sum()
            )

        units_col = self._find_column(
            supplier_orders,
            [
                "units",
                "quantity",
                "order_units"
            ]
        )

        total_units = 0

        if units_col:

            total_units = float(
                pd.to_numeric(
                    supplier_orders[units_col],
                    errors="coerce"
                )
                .fillna(0)
                .sum()
            )

        late_rate = (
            late_orders / total_orders
            if total_orders
            else 0
        )

        # ---------------------------------------------------------
        # Top orders
        # ---------------------------------------------------------

        top_orders = []

        if units_col:

            temp = supplier_orders.copy()

            temp["units_numeric"] = pd.to_numeric(
                temp[units_col],
                errors="coerce"
            ).fillna(0)

            columns = [
                column
                for column in [
                    "order_id",
                    "product_id",
                    units_col,
                    late_col
                ]
                if column is not None
                and column in temp.columns
            ]

            top_orders = (
                temp
                .sort_values(
                    "units_numeric",
                    ascending=False
                )[columns]
                .head(10)
                .to_dict(orient="records")
            )

        return {
            "status": "success",
            "supplier_id": supplier_id,

            "risk": risk,

            "evidence": {
                "total_orders": total_orders,
                "late_orders": late_orders,
                "late_rate": round(
                    late_rate,
                    4
                ),
                "total_units": round(
                    total_units,
                    2
                ),
                "top_orders": top_orders
            },

            "source": {
                "dataset": "order_features",
                "entity_column": supplier_col
            }
        }

    # =============================================================
    # INVENTORY EVIDENCE
    # =============================================================

    def inventory_evidence(
        self,
        product_id: str
    ) -> dict:

        result = self._load()

        datasets = result["datasets"]

        # ---------------------------------------------------------
        # IMPORTANT:
        # Use .get() so we can provide a meaningful error instead
        # of a raw KeyError like "'inventory'".
        # ---------------------------------------------------------

        inventory = datasets.get("inventory")

        demand = datasets.get("demand")

        if inventory is None:

            return {
                "status": "error",
                "product_id": product_id,
                "message": (
                    "Inventory dataset is not available. "
                    "Expected dataset key: inventory."
                )
            }

        # ---------------------------------------------------------
        # Find product column
        # ---------------------------------------------------------

        product_col = self._find_column(
            inventory,
            [
                "product_id",
                "product",
                "productid"
            ]
        )

        if product_col is None:

            return {
                "status": "error",
                "product_id": product_id,
                "message": (
                    "Product information is not available "
                    "in inventory data."
                )
            }

        # ---------------------------------------------------------
        # Filter product
        # ---------------------------------------------------------

        product_inventory = inventory[
            inventory[product_col].astype(str)
            == str(product_id)
        ].copy()

        if product_inventory.empty:

            return {
                "status": "not_found",
                "product_id": product_id,
                "message": (
                    f"No inventory evidence found for "
                    f"product {product_id}."
                )
            }

        # ---------------------------------------------------------
        # Calculate full inventory risk
        # ---------------------------------------------------------

        inventory_risk = self.inventory_analyzer.analyze(top_n=2000)

        risk_row = inventory_risk[
            inventory_risk["product_id"].astype(str)
            == str(product_id)
        ]

        risk = {}

        if not risk_row.empty:

            risk = risk_row.iloc[0].to_dict()

        # ---------------------------------------------------------
        # Inventory values
        # ---------------------------------------------------------

        inventory_col = self._find_column(
            product_inventory,
            [
                "inventory_units",
                "inventory",
                "stock",
                "stock_units"
            ]
        )

        inventory_values = []

        if inventory_col:

            inventory_values = (
                pd.to_numeric(
                    product_inventory[inventory_col],
                    errors="coerce"
                )
                .dropna()
                .tolist()
            )

        average_inventory = (
            float(
                sum(inventory_values)
                / len(inventory_values)
            )
            if inventory_values
            else None
        )

        minimum_inventory = (
            float(min(inventory_values))
            if inventory_values
            else None
        )

        zero_inventory_records = (
            sum(
                value <= 0
                for value in inventory_values
            )
            if inventory_values
            else 0
        )

        # ---------------------------------------------------------
        # Demand evidence
        # ---------------------------------------------------------

        average_daily_demand = None
        total_demand = None

        if demand is not None and not demand.empty:

            demand_product_col = self._find_column(
                demand,
                [
                    "product_id",
                    "product",
                    "productid"
                ]
            )

            demand_value_col = self._find_column(
                demand,
                [
                    "demand",
                    "demand_units",
                    "quantity",
                    "units"
                ]
            )

            if (
                demand_product_col is not None
                and demand_value_col is not None
            ):

                product_demand = demand[
                    demand[demand_product_col].astype(str)
                    == str(product_id)
                ].copy()

                if not product_demand.empty:

                    demand_values = pd.to_numeric(
                        product_demand[demand_value_col],
                        errors="coerce"
                    ).dropna()

                    if not demand_values.empty:

                        average_daily_demand = round(
                            float(demand_values.mean()),
                            2
                        )

                        total_demand = round(
                            float(demand_values.sum()),
                            2
                        )

        # ---------------------------------------------------------
        # Days of cover
        # ---------------------------------------------------------

        days_of_cover = None

        if (
            average_inventory is not None
            and average_daily_demand is not None
            and average_daily_demand > 0
        ):

            days_of_cover = round(
                average_inventory
                / average_daily_demand,
                2
            )

        # ---------------------------------------------------------
        # Demand pressure
        # ---------------------------------------------------------

        demand_pressure = None

        if (
            average_inventory is not None
            and average_daily_demand is not None
            and (
                average_inventory
                + average_daily_demand
            ) > 0
        ):

            demand_pressure = round(
                average_daily_demand
                /
                (
                    average_inventory
                    + average_daily_demand
                ),
                4
            )

        # ---------------------------------------------------------
        # Final evidence response
        # ---------------------------------------------------------

        return {
            "status": "success",

            "product_id": product_id,

            "risk": risk,

            "evidence": {

                "records": len(
                    product_inventory
                ),

                "average_inventory": (
                    round(
                        average_inventory,
                        2
                    )
                    if average_inventory is not None
                    else None
                ),

                "minimum_inventory": (
                    round(
                        minimum_inventory,
                        2
                    )
                    if minimum_inventory is not None
                    else None
                ),

                "zero_inventory_records":
                    zero_inventory_records,

                "average_daily_demand":
                    average_daily_demand,

                "total_demand":
                    total_demand,

                "days_of_cover":
                    days_of_cover,

                "demand_pressure":
                    demand_pressure
            },

            "source": {

                "datasets": [
                    "inventory_daily",
                    "demand_daily"
                ],

                "entity_column":
                    product_col
            }
        }

    # =============================================================
    # COLUMN FINDER
    # =============================================================

    def _find_column(
        self,
        df: pd.DataFrame,
        candidates: list[str]
    ) -> str | None:

        normalized = {
            str(column).strip().lower(): column
            for column in df.columns
        }

        for candidate in candidates:

            key = candidate.strip().lower()

            if key in normalized:

                return normalized[key]

        return None
    