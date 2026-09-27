import pandas as pd


class DataValidator:

    def validate_orders(
        self,
        df: pd.DataFrame
    ) -> dict:

        required_columns = [
            "order_id",
            "product_id",
            "units",
            "late_order"
        ]

        missing_columns = [
            col
            for col in required_columns
            if col not in df.columns
        ]

        return {
            "valid": len(missing_columns) == 0,
            "missing_columns": missing_columns,
            "rows": len(df),
            "duplicates": int(
                df["order_id"].duplicated().sum()
            ) if "order_id" in df.columns else None,
            "missing_values": int(
                df.isna().sum().sum()
            )
        }

    def validate_products(
        self,
        df: pd.DataFrame
    ) -> dict:

        required_columns = [
            "product_id"
        ]

        missing_columns = [
            col
            for col in required_columns
            if col not in df.columns
        ]

        return {
            "valid": len(missing_columns) == 0,
            "missing_columns": missing_columns,
            "rows": len(df)
        }

    def validate_suppliers(
        self,
        df: pd.DataFrame
    ) -> dict:

        required_columns = [
            "supplier_id"
        ]

        missing_columns = [
            col
            for col in required_columns
            if col not in df.columns
        ]

        return {
            "valid": len(missing_columns) == 0,
            "missing_columns": missing_columns,
            "rows": len(df)
        }

    def validate_all(
        self,
        datasets: dict[str, pd.DataFrame]
    ) -> dict:

        results = {}

        if "orders" in datasets:
            results["orders"] = self.validate_orders(
                datasets["orders"]
            )

        if "products" in datasets:
            results["products"] = self.validate_products(
                datasets["products"]
            )

        if "suppliers" in datasets:
            results["suppliers"] = self.validate_suppliers(
                datasets["suppliers"]
            )

        return results
    