from __future__ import annotations

import pandas as pd


class ProductSupplierAnalyzer:
    """Maps products to their supplying suppliers."""

    def analyze(
        self,
        products: pd.DataFrame,
        suppliers: pd.DataFrame | None = None,
        product_ids: list[str] | None = None,
        supplier_ids: list[str] | None = None,
        top_n: int | None = None,
    ) -> pd.DataFrame:
        if products is None or products.empty:
            return pd.DataFrame(
                columns=[
                    "product_id",
                    "supplier_id",
                    "supplier_name",
                ]
            )

        required_columns = {"product_id", "supplier_id"}
        missing = required_columns - set(products.columns)

        if missing:
            raise ValueError(
                "Missing required columns for product-supplier analysis: "
                f"{sorted(missing)}"
            )

        df = products[["product_id", "supplier_id"]].copy()
        df["product_id"] = df["product_id"].astype(str).str.upper()
        df["supplier_id"] = df["supplier_id"].astype(str).str.upper()
        df = df.dropna(subset=["product_id", "supplier_id"]).drop_duplicates()

        if product_ids:
            normalized = {str(pid).upper() for pid in product_ids if pid is not None}
            if normalized:
                df = df[df["product_id"].isin(normalized)].copy()

        if supplier_ids:
            normalized = {
                str(sid).upper() for sid in supplier_ids if sid is not None
            }
            if normalized:
                df = df[df["supplier_id"].isin(normalized)].copy()

        if suppliers is not None and not suppliers.empty:
            supplier_columns = [
                column for column in ["supplier_id", "supplier_name"]
                if column in suppliers.columns
            ]
            if supplier_columns:
                supplier_map = suppliers[supplier_columns].copy()
                supplier_map["supplier_id"] = (
                    supplier_map["supplier_id"].astype(str).str.upper()
                )
                df = df.merge(
                    supplier_map,
                    on="supplier_id",
                    how="left",
                )

        if "supplier_name" not in df.columns:
            df["supplier_name"] = None

        df = df.sort_values(["product_id", "supplier_id"]).reset_index(drop=True)

        if top_n is not None:
            df = df.head(top_n)

        return df[["product_id", "supplier_id", "supplier_name"]].reset_index(drop=True)
