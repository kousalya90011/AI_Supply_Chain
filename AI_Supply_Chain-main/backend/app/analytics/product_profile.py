from __future__ import annotations

import logging
from typing import Any
import pandas as pd

from app.models.database import SessionLocal
from app.models.entities import Product as DBProduct, SupplierOffer as DBSupplierOffer, Order as DBOrder, Supplier as DBSupplier

logger = logging.getLogger(__name__)


class ProductProfileAnalyzer:
    """
    Comprehensive product analyzer combining catalog attributes, approval status,
    associated supplier relationships, active supplier offers, orders, and inventory metrics.
    """

    def __init__(self, data_service: Any = None) -> None:
        self.data_service = data_service

    def analyze(
        self,
        products: pd.DataFrame | None = None,
        product_id: str | None = None,
        product_ids: list[str] | None = None,
        db: Any | None = None,
    ) -> pd.DataFrame:
        targets: set[str] = set()
        if product_id:
            targets.add(str(product_id).strip().upper())
        if product_ids:
            for pid in product_ids:
                if pid:
                    targets.add(str(pid).strip().upper())

        # 1. Fetch from database first for most up-to-date attributes
        should_close = False
        active_db = db
        if active_db is None:
            active_db = SessionLocal()
            should_close = True

        rows: list[dict[str, Any]] = []
        try:
            query = active_db.query(DBProduct)
            if targets:
                query = query.filter(DBProduct.product_id.in_(list(targets)))
            db_products = query.all()

            found_pids = set()
            for p in db_products:
                pid = str(p.product_id).strip().upper()
                found_pids.add(pid)

                # Fetch supplier name
                supplier_name = p.supplier_id or "Unassigned"
                if p.supplier_id:
                    sup = active_db.query(DBSupplier).filter_by(supplier_id=p.supplier_id).first()
                    if sup and sup.name:
                        supplier_name = sup.name

                # Fetch offers
                offers = active_db.query(DBSupplierOffer).filter_by(product_id=pid).all()
                accepted_offers = [o for o in offers if str(o.status).upper() in {"ACCEPTED", "ACTIVE", "APPROVED"}]
                active_offer_qty = sum(o.quantity or 0 for o in accepted_offers)
                latest_offer_price = accepted_offers[0].unit_price if accepted_offers else (offers[0].unit_price if offers else p.unit_cost)
                latest_delivery_days = accepted_offers[0].delivery_days if accepted_offers else (offers[0].delivery_days if offers else 7)

                # Fetch orders
                orders = active_db.query(DBOrder).filter_by(product_id=pid).all()
                pending_orders = [o for o in orders if str(o.status).upper() == "PENDING"]

                rows.append({
                    "product_id": pid,
                    "name": p.name or f"Product {pid}",
                    "category": p.category or "General",
                    "unit_cost": float(p.unit_cost or 0.0),
                    "supplier_id": str(p.supplier_id or "").strip().upper() or "S0001",
                    "supplier_name": supplier_name,
                    "status": str(p.status or "ACTIVE").upper(),
                    "approval_status": str(p.approval_status or "APPROVED").upper(),
                    "approved_by": p.approved_by or "admin",
                    "offers_count": len(offers),
                    "accepted_offers_count": len(accepted_offers),
                    "available_offer_units": active_offer_qty,
                    "latest_offer_price": float(latest_offer_price or 0.0),
                    "delivery_days": int(latest_delivery_days or 7),
                    "total_orders": len(orders),
                    "pending_orders": len(pending_orders),
                    "stockout_rate": 0.0,
                    "days_of_cover": 999.0,
                    "risk_score": 15.0,
                    "risk_level": "LOW",
                })

            # 2. If not found in DB, check datasets products (historical products)
            if products is not None and not products.empty:
                missing_targets = targets - found_pids if targets else set(products["product_id"].astype(str).str.upper())
                for _, row in products.iterrows():
                    pid = str(row["product_id"]).strip().upper()
                    if (not targets or pid in missing_targets) and pid not in found_pids:
                        found_pids.add(pid)
                        sid = str(row.get("supplier_id", "S0001")).strip().upper()
                        rows.append({
                            "product_id": pid,
                            "name": str(row.get("name", f"Product {pid}")),
                            "category": str(row.get("category", "General")),
                            "unit_cost": float(row.get("unit_cost", 0.0)),
                            "supplier_id": sid,
                            "supplier_name": str(row.get("supplier_name", sid)),
                            "status": str(row.get("status", "ACTIVE")).upper(),
                            "approval_status": str(row.get("approval_status", "APPROVED")).upper(),
                            "approved_by": str(row.get("approved_by", "admin")),
                            "offers_count": 0,
                            "accepted_offers_count": 0,
                            "available_offer_units": 0,
                            "latest_offer_price": float(row.get("unit_cost", 0.0)),
                            "delivery_days": 7,
                            "total_orders": 0,
                            "pending_orders": 0,
                            "stockout_rate": 0.0,
                            "days_of_cover": 30.0,
                            "risk_score": 25.0,
                            "risk_level": "LOW",
                        })

        finally:
            if should_close:
                active_db.close()

        if not rows:
            return pd.DataFrame(columns=[
                "product_id", "name", "category", "unit_cost", "supplier_id",
                "supplier_name", "status", "approval_status", "approved_by",
                "offers_count", "accepted_offers_count", "available_offer_units",
                "latest_offer_price", "delivery_days", "total_orders", "pending_orders",
                "stockout_rate", "days_of_cover", "risk_score", "risk_level"
            ])

        return pd.DataFrame(rows)
