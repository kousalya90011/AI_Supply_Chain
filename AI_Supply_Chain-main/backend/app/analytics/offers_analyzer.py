from __future__ import annotations

from typing import Any
import pandas as pd

from app.models.database import SessionLocal
from app.models.entities import SupplierOffer


class OffersAnalyzer:
    """
    Deterministic analytics analyzer for supplier offers.
    Queries the supplier_offers database table and returns a DataFrame.
    """

    def analyze(
        self,
        supplier_id: str | None = None,
        product_id: str | None = None,
        supplier_ids: list[str] | None = None,
        product_ids: list[str] | None = None,
        top_n: int | None = None,
        db: Any | None = None,
    ) -> pd.DataFrame:
        should_close = False
        active_db = db
        if active_db is None:
            active_db = SessionLocal()
            should_close = True

        try:
            query = active_db.query(SupplierOffer)

            if supplier_id:
                query = query.filter(
                    SupplierOffer.supplier_id == str(supplier_id).strip().upper()
                )

            if supplier_ids:
                allowed_sids = [
                    str(s).strip().upper() for s in supplier_ids if s is not None
                ]
                if allowed_sids:
                    query = query.filter(SupplierOffer.supplier_id.in_(allowed_sids))

            if product_id:
                query = query.filter(
                    SupplierOffer.product_id == str(product_id).strip().upper()
                )

            if product_ids:
                allowed_pids = [
                    str(p).strip().upper() for p in product_ids if p is not None
                ]
                if allowed_pids:
                    query = query.filter(SupplierOffer.product_id.in_(allowed_pids))

            offers = query.order_by(SupplierOffer.created_at.desc()).all()

            if not offers:
                return pd.DataFrame(
                    columns=[
                        "offer_id",
                        "supplier_id",
                        "product_id",
                        "quantity",
                        "unit_price",
                        "delivery_days",
                        "status",
                        "valid_until",
                    ]
                )

            records = [
                {
                    "offer_id": o.offer_id,
                    "supplier_id": o.supplier_id,
                    "product_id": o.product_id,
                    "quantity": o.quantity,
                    "unit_price": float(o.unit_price) if o.unit_price is not None else 0.0,
                    "delivery_days": o.delivery_days,
                    "status": o.status,
                    "valid_until": o.valid_until.isoformat() if o.valid_until else None,
                }
                for o in offers
            ]

            df = pd.DataFrame(records)
            if top_n is not None and top_n > 0:
                df = df.head(top_n)

            return df
        finally:
            if should_close:
                active_db.close()
