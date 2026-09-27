import numpy as np
import pandas as pd


class FeatureEngineer:

    def create_order_features(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:

        df = df.copy()

        # Delay-related feature
        if "late_order" in df.columns:
            df["delay_flag"] = (
                df["late_order"]
                .fillna(0)
                .astype(int)
            )

        # Unit risk
        if "units" in df.columns:

            df["high_volume_order"] = (
                df["units"]
                >= df["units"].quantile(0.90)
            ).astype(int)

        # Cost exposure
        if {
            "units",
            "unit_cost"
        }.issubset(df.columns):

            df["order_cost"] = (
                df["units"] *
                df["unit_cost"]
            )

        # Lead-time risk
        if "lead_time_days" in df.columns:

            mean_lead = df[
                "lead_time_days"
            ].mean()

            std_lead = df[
                "lead_time_days"
            ].std()

            df["lead_time_anomaly"] = (
                np.abs(
                    df["lead_time_days"]
                    - mean_lead
                ) > 2 * std_lead
            ).astype(int)

        return df

    def create_supplier_features(
        self,
        orders: pd.DataFrame
    ) -> pd.DataFrame:

        required = {
            "supplier_id",
            "order_id",
            "units",
            "late_order"
        }

        if not required.issubset(orders.columns):

            return pd.DataFrame()

        supplier = (
            orders
            .groupby("supplier_id")
            .agg(
                total_orders=(
                    "order_id",
                    "count"
                ),
                total_units=(
                    "units",
                    "sum"
                ),
                late_orders=(
                    "late_order",
                    "sum"
                )
            )
            .reset_index()
        )

        supplier["late_rate"] = (
            supplier["late_orders"]
            / supplier["total_orders"]
        )

        supplier["supplier_risk_score"] = (
            supplier["late_rate"] * 100
        )

        supplier["risk_level"] = pd.cut(
            supplier["supplier_risk_score"],
            bins=[
                -1,
                30,
                60,
                80,
                101
            ],
            labels=[
                "LOW",
                "MEDIUM",
                "HIGH",
                "CRITICAL"
            ]
        )

        return supplier
    