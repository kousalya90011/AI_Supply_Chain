import pandas as pd


class DashboardMetrics:

    def calculate(
        self,
        orders: pd.DataFrame,
        inventory: pd.DataFrame
    ) -> dict:

        total_orders = len(orders)

        late_orders = int(
            orders["late_order"]
            .sum()
        )

        late_rate = (
            late_orders / total_orders
            if total_orders
            else 0
        )

        high_risk_inventory = int(
            (
                inventory["inventory_units"]
                <= 0
            ).sum()
        )

        total_units = int(
            orders["units"].sum()
        )

        total_order_value = float(
            orders["order_value"].sum()
            if "order_value" in orders.columns
            else 0
        )

        return {

            "total_orders":
                total_orders,

            "late_orders":
                late_orders,

            "late_rate":
                round(
                    late_rate * 100,
                    2
                ),

            "total_units":
                total_units,

            "inventory_stockout_records":
                high_risk_inventory,

            "total_order_value":
                round(
                    total_order_value,
                    2
                )
        }
    