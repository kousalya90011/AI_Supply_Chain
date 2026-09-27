from __future__ import annotations

import pandas as pd


class SupplierInventoryImpactAnalyzer:

    def analyze(
        self,
        orders: pd.DataFrame,
        inventory: pd.DataFrame,
        supplier_id: str | None = None,
        top_n: int = 10
    ) -> dict:

        if orders is None or orders.empty:
            return {
                "status": "success",
                "supplier": None,
                "products": [],
                "evidence": []
            }

        orders_df = orders.copy()
        inventory_df = inventory.copy()

        required_order_columns = {
            "supplier_id",
            "product_id",
            "late_order",
            "delay_days",
            "units",
            "order_id"
        }

        missing = required_order_columns - set(
            orders_df.columns
        )

        if missing:
            raise ValueError(
                "Missing required order columns: "
                f"{sorted(missing)}"
            )

        # -----------------------------------------------------
        # FILTER SUPPLIER
        # -----------------------------------------------------

        if supplier_id:
            orders_df = orders_df[
                orders_df["supplier_id"].astype(str).str.upper()
                == supplier_id.upper()
            ]

        if orders_df.empty:
            return {
                "status": "success",
                "supplier": supplier_id,
                "products": [],
                "evidence": []
            }

        # -----------------------------------------------------
        # SUPPLIER SUMMARY
        # -----------------------------------------------------

        supplier_name = supplier_id

        if "supplier_name" in orders_df.columns:
            names = (
                orders_df["supplier_name"]
                .dropna()
                .astype(str)
                .unique()
            )

            if len(names) > 0:
                supplier_name = names[0]

        total_orders = len(orders_df)

        late_orders = int(
            pd.to_numeric(
                orders_df["late_order"],
                errors="coerce"
            ).fillna(0).sum()
        )

        late_rate = (
            late_orders / total_orders
            if total_orders
            else 0
        )

        average_delay = float(
            pd.to_numeric(
                orders_df["delay_days"],
                errors="coerce"
            ).fillna(0).mean()
        )

        total_units = float(
            pd.to_numeric(
                orders_df["units"],
                errors="coerce"
            ).fillna(0).sum()
        )

        # -----------------------------------------------------
        # PRODUCT IMPACT
        # -----------------------------------------------------

        product_summary = (
            orders_df
            .groupby("product_id")
            .agg(
                order_count=("order_id", "count"),
                total_units=("units", "sum"),
                late_orders=("late_order", "sum"),
                average_delay=("delay_days", "mean")
            )
            .reset_index()
        )

        product_summary["late_rate"] = (
            product_summary["late_orders"]
            / product_summary["order_count"]
        )

        # -----------------------------------------------------
        # INVENTORY
        # -----------------------------------------------------

        if (
            inventory_df is not None
            and not inventory_df.empty
            and "product_id" in inventory_df.columns
            and "inventory_units" in inventory_df.columns
        ):

            inventory_df["inventory_units"] = pd.to_numeric(
                inventory_df["inventory_units"],
                errors="coerce"
            )

            inventory_summary = (
                inventory_df
                .groupby("product_id")
                .agg(
                    average_inventory=("inventory_units", "mean"),
                    minimum_inventory=("inventory_units", "min"),
                    zero_inventory_days=(
                        "inventory_units",
                        lambda x: int((x <= 0).sum())
                    ),
                    inventory_days=("inventory_units", "count")
                )
                .reset_index()
            )

            inventory_summary["stockout_rate"] = (
                inventory_summary["zero_inventory_days"]
                / inventory_summary["inventory_days"]
            )

            product_summary = product_summary.merge(
                inventory_summary,
                on="product_id",
                how="left"
            )

        else:

            product_summary["average_inventory"] = None
            product_summary["minimum_inventory"] = None
            product_summary["zero_inventory_days"] = None
            product_summary["inventory_days"] = None
            product_summary["stockout_rate"] = None

        # -----------------------------------------------------
        # IMPACT SCORE
        # -----------------------------------------------------

        product_summary["late_rate"] = (
            product_summary["late_rate"]
            .fillna(0)
        )

        product_summary["stockout_rate"] = (
            product_summary["stockout_rate"]
            .fillna(0)
        )

        product_summary["impact_score"] = (
            0.40
            * product_summary["late_rate"]
            * 100
            +
            0.30
            * product_summary["stockout_rate"]
            * 100
            +
            0.20
            * (
                product_summary["total_units"]
                /
                max(
                    product_summary["total_units"].max(),
                    1
                )
            )
            * 100
            +
            0.10
            * (
                product_summary["average_delay"]
                /
                max(
                    product_summary["average_delay"].max(),
                    1
                )
            )
            * 100
        )

        product_summary["impact_score"] = (
            product_summary["impact_score"]
            .clip(0, 100)
            .round(2)
        )

        product_summary = product_summary.sort_values(
            "impact_score",
            ascending=False
        ).head(top_n)

        products = product_summary.to_dict(
            orient="records"
        )

        # -----------------------------------------------------
        # EVIDENCE CHAIN
        # -----------------------------------------------------

        evidence = []

        for product in products:

            evidence.append({
                "supplier_id": supplier_id,
                "supplier_name": supplier_name,
                "product_id": product["product_id"],
                "order_count": int(product["order_count"]),
                "total_units": float(product["total_units"]),
                "late_orders": int(product["late_orders"]),
                "supplier_product_late_rate": round(
                    float(product["late_rate"]),
                    4
                ),
                "average_delay_days": round(
                    float(product["average_delay"]),
                    2
                ),
                "average_inventory": round(
                    float(product["average_inventory"]),
                    2
                )
                if pd.notna(product["average_inventory"])
                else None,
                "minimum_inventory": round(
                    float(product["minimum_inventory"]),
                    2
                )
                if pd.notna(product["minimum_inventory"])
                else None,
                "stockout_rate": round(
                    float(product["stockout_rate"]),
                    4
                ),
                "impact_score": float(
                    product["impact_score"]
                )
            })

        return {
            "status": "success",
            "supplier": {
                "supplier_id": supplier_id,
                "supplier_name": supplier_name,
                "total_orders": total_orders,
                "late_orders": late_orders,
                "late_rate": round(late_rate, 4),
                "average_delay_days": round(
                    average_delay,
                    2
                ),
                "total_units": total_units
            },
            "products": products,
            "evidence": evidence
        }