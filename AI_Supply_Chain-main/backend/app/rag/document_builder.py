from __future__ import annotations

import logging
from typing import Any
import pandas as pd
from sqlalchemy.orm import Session

from app.analytics.inventory_risk import InventoryRiskAnalyzer
from app.analytics.product_sales import ProductSalesAnalyzer
from app.analytics.product_supplier import ProductSupplierAnalyzer
from app.analytics.supplier_risk import SupplierRiskAnalyzer
from app.models.database import SessionLocal
from app.models.entities import Order as DBOrder, SupplierOffer as DBSupplierOffer
from app.rag.schemas import KnowledgeDocument
from app.services.data_service import DataService

logger = logging.getLogger(__name__)


class KnowledgeDocumentBuilder:
    """
    Builds semantic summary knowledge documents for products and suppliers
    from aggregated deterministic analytics and live transactional database records.
    """

    def __init__(self, data_service: DataService | None = None) -> None:
        self.data_service = data_service or DataService()

    def build_all_documents(
        self,
        db: Session | None = None,
    ) -> list[KnowledgeDocument]:
        """
        Builds all product and supplier knowledge documents.
        """
        data = self.data_service.load_data()
        datasets = data.get("datasets", {})

        products_df = datasets.get("products")
        suppliers_df = datasets.get("suppliers")
        orders_extended = datasets.get("orders_extended")

        should_close = False
        active_db = db
        if active_db is None:
            active_db = SessionLocal()
            should_close = True

        try:
            product_docs = self.build_product_documents(
                datasets=datasets,
                db=active_db,
            )
            supplier_docs = self.build_supplier_documents(
                datasets=datasets,
                db=active_db,
            )
            return product_docs + supplier_docs
        finally:
            if should_close:
                active_db.close()

    def build_product_documents(
        self,
        datasets: dict[str, pd.DataFrame] | None = None,
        db: Session | None = None,
    ) -> list[KnowledgeDocument]:
        """
        Generates one semantic knowledge document per product.
        """
        if datasets is None:
            data = self.data_service.load_data()
            datasets = data.get("datasets", {})

        products_df = datasets.get("products")
        if products_df is None or products_df.empty:
            return []

        # 1. Run deterministic inventory & risk analyzer
        inv_analyzer = InventoryRiskAnalyzer(self.data_service)
        try:
            inv_risk_df = inv_analyzer.analyze()
            inv_by_product = (
                inv_risk_df.set_index("product_id").to_dict(orient="index")
                if not inv_risk_df.empty and "product_id" in inv_risk_df.columns
                else {}
            )
        except Exception as e:
            logger.warning(f"Error computing inventory risk for product docs: {e}")
            inv_by_product = {}

        # 2. Run product sales analyzer
        sales_analyzer = ProductSalesAnalyzer()
        try:
            sales_df = sales_analyzer.analyze(
                orders=datasets.get("orders_extended"),
            )
            sales_by_product = (
                sales_df.set_index("product_id").to_dict(orient="index")
                if not sales_df.empty and "product_id" in sales_df.columns
                else {}
            )
        except Exception as e:
            logger.warning(f"Error computing sales for product docs: {e}")
            sales_by_product = {}

        # 3. Product-supplier mappings
        prod_sup_analyzer = ProductSupplierAnalyzer()
        try:
            ps_df = prod_sup_analyzer.analyze(
                products=products_df,
                suppliers=datasets.get("suppliers"),
            )
            suppliers_by_product: dict[str, list[dict[str, str]]] = {}
            for _, row in ps_df.iterrows():
                pid = str(row["product_id"]).upper()
                sid = str(row["supplier_id"]).upper()
                sname = str(row.get("supplier_name", sid))
                suppliers_by_product.setdefault(pid, []).append(
                    {"supplier_id": sid, "supplier_name": sname}
                )
        except Exception as e:
            logger.warning(f"Error mapping product suppliers: {e}")
            suppliers_by_product = {}

        # 4. Live transactional data from database
        db_offers_by_prod: dict[str, dict[str, int]] = {}
        db_orders_by_prod: dict[str, dict[str, Any]] = {}
        if db is not None:
            try:
                offers = db.query(DBSupplierOffer).all()
                for off in offers:
                    pid = str(off.product_id).upper()
                    st = str(off.status).upper()
                    db_offers_by_prod.setdefault(
                        pid, {"total": 0, "PENDING": 0, "ACCEPTED": 0, "REJECTED": 0, "WITHDRAWN": 0}
                    )
                    db_offers_by_prod[pid]["total"] += 1
                    if st in db_offers_by_prod[pid]:
                        db_offers_by_prod[pid][st] += 1

                db_orders = db.query(DBOrder).all()
                for ord_item in db_orders:
                    pid = str(ord_item.product_id).upper()
                    db_orders_by_prod.setdefault(pid, {"count": 0, "units": 0})
                    db_orders_by_prod[pid]["count"] += 1
                    db_orders_by_prod[pid]["units"] += int(ord_item.quantity or 0)
            except Exception as e:
                logger.warning(f"Error reading transactional DB state for products: {e}")

        # 5. Generate documents
        documents: list[KnowledgeDocument] = []
        for _, prod_row in products_df.iterrows():
            pid = str(prod_row["product_id"]).upper()
            category = str(prod_row.get("category", "General"))
            unit_cost = float(prod_row.get("unit_cost", 0.0))

            # Suppliers for this product
            sups = suppliers_by_product.get(pid, [])
            sup_ids = [s["supplier_id"] for s in sups]
            if not sup_ids and "supplier_id" in prod_row and pd.notna(prod_row["supplier_id"]):
                fallback_sid = str(prod_row["supplier_id"]).upper()
                sup_ids = [fallback_sid]
                sups = [{"supplier_id": fallback_sid, "supplier_name": fallback_sid}]

            sup_names = [s.get("supplier_name", s["supplier_id"]) for s in sups]
            sup_desc = ", ".join(f"{s['supplier_name']} ({s['supplier_id']})" for s in sups) if sups else "Unassigned"

            # Inventory & Risk stats
            inv_stats = inv_by_product.get(pid, {})
            avg_inv = float(inv_stats.get("avg_inventory", 0.0))
            zero_inv_days = int(inv_stats.get("zero_inventory_days", 0))
            stockout_rate = float(inv_stats.get("stockout_rate", 0.0))
            days_of_cover = float(inv_stats.get("days_of_cover", 0.0))
            avg_daily_demand = float(inv_stats.get("average_daily_demand", 0.0))
            risk_score = float(inv_stats.get("risk_score", 0.0))
            risk_level = str(inv_stats.get("risk_level", "LOW"))
            risk_reason = str(inv_stats.get("risk_reason", f"Risk score {risk_score:.1f}"))

            # Sales stats
            sales_stats = sales_by_product.get(pid, {})
            total_demand = float(sales_stats.get("total_demand", avg_daily_demand * 30))
            total_sales = float(sales_stats.get("total_sales", 0.0))

            # Transactional stats
            tx_offers = db_offers_by_prod.get(
                pid, {"total": 0, "PENDING": 0, "ACCEPTED": 0, "REJECTED": 0, "WITHDRAWN": 0}
            )
            tx_orders = db_orders_by_prod.get(pid, {"count": 0, "units": 0})

            # Build semantic content summary
            content_lines = [
                f"Product {pid} Summary & Operational Risk Profile:",
                f"- Category: {category}",
                f"- Unit Cost: ${unit_cost:.2f}",
                f"- Suppliers: {sup_desc}",
                f"- Demand Metrics: Total demand is {total_demand:,.0f} units with average daily demand of {avg_daily_demand:.1f} units.",
                f"- Inventory Status: Average inventory is {avg_inv:,.1f} units. Days of inventory cover: {days_of_cover:.1f} days.",
                f"- Stockout & Reliability: Zero-inventory days recorded: {zero_inv_days} days, giving a stockout rate of {stockout_rate * 100:.2f}%.",
                f"- Supply Chain Risk: Evaluated at {risk_score:.1f}/100 ({risk_level} Risk). Reason: {risk_reason}.",
            ]

            if tx_offers["total"] > 0:
                content_lines.append(
                    f"- Live Supplier Offers: {tx_offers['total']} offers ({tx_offers['PENDING']} pending, "
                    f"{tx_offers['ACCEPTED']} accepted, {tx_offers['REJECTED']} rejected)."
                )
            if tx_orders["count"] > 0:
                content_lines.append(
                    f"- Live Transactional Orders: {tx_orders['count']} orders totaling {tx_orders['units']:,} units."
                )

            summary_text = "\n".join(content_lines)

            metadata = {
                "document_type": "product",
                "entity_id": pid,
                "supplier_ids": sup_ids,
                "product_ids": [pid],
                "category": category,
                "unit_cost": unit_cost,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "stockout_rate": round(stockout_rate, 4),
                "avg_inventory": round(avg_inv, 2),
                "days_of_cover": round(days_of_cover, 2),
                "total_demand": round(total_demand, 2),
                "source": "hybrid",
            }

            doc = KnowledgeDocument(
                doc_id=f"product:{pid}",
                doc_type="product",
                entity_id=pid,
                title=f"Product {pid} ({category})",
                content=summary_text,
                metadata=metadata,
            )
            documents.append(doc)

        return documents

    def build_supplier_documents(
        self,
        datasets: dict[str, pd.DataFrame] | None = None,
        db: Session | None = None,
    ) -> list[KnowledgeDocument]:
        """
        Generates one semantic knowledge document per supplier.
        """
        if datasets is None:
            data = self.data_service.load_data()
            datasets = data.get("datasets", {})

        suppliers_df = datasets.get("suppliers")
        orders_extended = datasets.get("orders_extended")
        products_df = datasets.get("products")

        if suppliers_df is None or suppliers_df.empty:
            return []

        # 1. Run supplier risk analyzer
        sup_analyzer = SupplierRiskAnalyzer()
        try:
            if orders_extended is not None and not orders_extended.empty:
                sup_risk_df = sup_analyzer.analyze(orders_extended)
                sup_risk_by_id = (
                    sup_risk_df.set_index("supplier_id").to_dict(orient="index")
                    if not sup_risk_df.empty and "supplier_id" in sup_risk_df.columns
                    else {}
                )
            else:
                sup_risk_by_id = {}
        except Exception as e:
            logger.warning(f"Error computing supplier risk: {e}")
            sup_risk_by_id = {}

        # 2. Map products supplied
        prod_sup_analyzer = ProductSupplierAnalyzer()
        try:
            ps_df = prod_sup_analyzer.analyze(
                products=products_df,
                suppliers=suppliers_df,
            )
            products_by_supplier: dict[str, list[str]] = {}
            for _, row in ps_df.iterrows():
                pid = str(row["product_id"]).upper()
                sid = str(row["supplier_id"]).upper()
                products_by_supplier.setdefault(sid, []).append(pid)
        except Exception as e:
            logger.warning(f"Error mapping supplier products: {e}")
            products_by_supplier = {}

        # 3. Live transactional data from database
        db_offers_by_sup: dict[str, dict[str, int]] = {}
        db_orders_by_sup: dict[str, dict[str, Any]] = {}
        if db is not None:
            try:
                offers = db.query(DBSupplierOffer).all()
                for off in offers:
                    sid = str(off.supplier_id).upper()
                    st = str(off.status).upper()
                    db_offers_by_sup.setdefault(
                        sid, {"total": 0, "PENDING": 0, "ACCEPTED": 0, "REJECTED": 0, "WITHDRAWN": 0}
                    )
                    db_offers_by_sup[sid]["total"] += 1
                    if st in db_offers_by_sup[sid]:
                        db_offers_by_sup[sid][st] += 1

                db_orders = db.query(DBOrder).all()
                for ord_item in db_orders:
                    sid = str(ord_item.supplier_id).upper()
                    db_orders_by_sup.setdefault(sid, {"count": 0, "units": 0})
                    db_orders_by_sup[sid]["count"] += 1
                    db_orders_by_sup[sid]["units"] += int(ord_item.quantity or 0)
            except Exception as e:
                logger.warning(f"Error reading transactional DB state for suppliers: {e}")

        # 4. Generate documents
        documents: list[KnowledgeDocument] = []
        for _, sup_row in suppliers_df.iterrows():
            sid = str(sup_row["supplier_id"]).upper()
            sname = str(sup_row.get("supplier_name", sup_row.get("name", sid)))
            region = str(sup_row.get("region", "Global"))
            tier = str(sup_row.get("tier", "Standard"))

            prods = products_by_supplier.get(sid, [])
            prod_desc = f"{len(prods)} products (" + ", ".join(prods[:5]) + ("..." if len(prods) > 5 else "") + ")" if prods else "None"

            # Performance stats
            perf = sup_risk_by_id.get(sid, {})
            total_orders = int(perf.get("total_orders", 0))
            total_units = int(perf.get("total_units", 0))
            late_orders = int(perf.get("late_orders", 0))
            late_rate = float(perf.get("late_rate", 0.0))
            risk_score = float(perf.get("risk_score", 20.0))
            risk_level = str(perf.get("risk_level", "LOW"))
            risk_reason = str(perf.get("risk_reason", f"Late rate: {late_rate * 100:.1f}%"))

            # Transactional stats
            tx_offers = db_offers_by_sup.get(
                sid, {"total": 0, "PENDING": 0, "ACCEPTED": 0, "REJECTED": 0, "WITHDRAWN": 0}
            )
            tx_orders = db_orders_by_sup.get(sid, {"count": 0, "units": 0})

            content_lines = [
                f"Supplier {sid} ({sname}) Performance & Relationship Profile:",
                f"- Region & Classification: Operating in {region} as a Tier {tier} supplier.",
                f"- Products Supplied: Supplies {prod_desc}.",
                f"- Order History: {total_orders:,} total orders executed with {total_units:,} units delivered.",
                f"- Delivery Reliability: {late_orders:,} late orders resulting in a late delivery rate of {late_rate * 100:.2f}%.",
                f"- Supplier Risk Assessment: Score {risk_score:.1f}/100 categorized as {risk_level} Risk. Details: {risk_reason}.",
            ]

            if tx_offers["total"] > 0:
                content_lines.append(
                    f"- Active Offer Proposals: {tx_offers['total']} offers ({tx_offers['PENDING']} pending review, "
                    f"{tx_offers['ACCEPTED']} accepted, {tx_offers['REJECTED']} rejected)."
                )
            if tx_orders["count"] > 0:
                content_lines.append(
                    f"- Recent Direct Orders: {tx_orders['count']} orders totaling {tx_orders['units']:,} units."
                )

            summary_text = "\n".join(content_lines)

            metadata = {
                "document_type": "supplier",
                "entity_id": sid,
                "supplier_ids": [sid],
                "product_ids": prods,
                "supplier_name": sname,
                "region": region,
                "tier": tier,
                "total_orders": total_orders,
                "total_units": total_units,
                "late_rate": round(late_rate, 4),
                "risk_score": risk_score,
                "risk_level": risk_level,
                "pending_offers": tx_offers["PENDING"],
                "accepted_offers": tx_offers["ACCEPTED"],
                "rejected_offers": tx_offers["REJECTED"],
                "source": "hybrid",
            }

            doc = KnowledgeDocument(
                doc_id=f"supplier:{sid}",
                doc_type="supplier",
                entity_id=sid,
                title=f"Supplier {sid} - {sname}",
                content=summary_text,
                metadata=metadata,
            )
            documents.append(doc)

        return documents
