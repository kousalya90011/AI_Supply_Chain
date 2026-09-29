from __future__ import annotations

import pandas as pd

from app.data.loader import DataLoader
from app.data.validator import DataValidator
from app.data.preprocessing import DataPreprocessor
from app.data.feature_engineering import FeatureEngineer


class DataService:

    def __init__(self):
        self.loader = DataLoader()
        self.validator = DataValidator()
        self.preprocessor = DataPreprocessor()
        self.feature_engineer = FeatureEngineer()
        self._cached_base = None

    def _get_base_data(self):
        if self._cached_base is not None:
            return self._cached_base

        # 1. Load raw datasets
        datasets = self.loader.load_all()

        # 2. Validate datasets
        validation = self.validator.validate_all(datasets)

        # 3. Clean / preprocess
        datasets = self.preprocessor.clean_all(datasets)

        # 4. Create engineered order features
        order_features = self.feature_engineer.create_order_features(
            datasets["orders_extended"]
        )
        datasets["order_features"] = order_features

        self._cached_base = {
            "datasets": datasets,
            "validation": validation,
        }
        return self._cached_base

    def load_data(self):
        base = self._get_base_data()
        datasets = {k: v.copy() for k, v in base["datasets"].items()}

        # Merge live database products and orders
        try:
            from app.models.database import SessionLocal
            from app.models.entities import Product as DBProduct, Order as DBOrder
            with SessionLocal() as session:
                db_prods = session.query(DBProduct).all()
                if db_prods and "products" in datasets:
                    existing_pids = set(datasets["products"]["product_id"].astype(str).str.upper())
                    new_prod_rows = []
                    for p in db_prods:
                        pid = str(p.product_id).strip().upper()
                        if pid not in existing_pids:
                            new_prod_rows.append({
                                "product_id": pid,
                                "name": p.name,
                                "category": p.category or "General",
                                "unit_cost": float(p.unit_cost or 0.0),
                                "supplier_id": str(p.supplier_id or "").strip().upper(),
                                "weight": 1.0,
                                "material_handling": "STANDARD",
                                "status": p.status,
                                "approval_status": p.approval_status,
                            })
                    if new_prod_rows:
                        datasets["products"] = pd.concat([datasets["products"], pd.DataFrame(new_prod_rows)], ignore_index=True)

                db_orders = session.query(DBOrder).all()
                if db_orders and "orders_extended" in datasets:
                    existing_oids = set(datasets["orders_extended"]["order_id"])
                    new_ord_rows = []
                    for o in db_orders:
                        if o.order_id not in existing_oids:
                            new_ord_rows.append({
                                "order_id": o.order_id,
                                "product_id": str(o.product_id).strip().upper(),
                                "supplier_id": str(o.supplier_id or "").strip().upper(),
                                "units": o.quantity or 0,
                                "quantity": o.quantity or 0,
                                "unit_cost": float(o.unit_price or 0.0),
                                "total_amount": float((o.quantity or 0) * (o.unit_price or 0.0)),
                                "order_date": str(o.order_date or ""),
                                "status": o.status or "PENDING",
                                "late": 0,
                                "delivery_delay": 0,
                                "lead_time_days": 7.0,
                                "disruption": 0,
                            })
                    if new_ord_rows:
                        datasets["orders_extended"] = pd.concat([datasets["orders_extended"], pd.DataFrame(new_ord_rows)], ignore_index=True)
        except Exception:
            pass

        return {
            "datasets": datasets,
            "validation": base["validation"],
        }
    