from __future__ import annotations

import logging
from typing import Any
import pandas as pd
from sqlalchemy.orm import Session

from app.analytics.inventory_risk import InventoryRiskAnalyzer
from app.analytics.product_sales import ProductSalesAnalyzer
from app.analytics.product_supplier import ProductSupplierAnalyzer
from app.analytics.supplier_risk import SupplierRiskAnalyzer
from app.analytics.lead_time_anomaly import LeadTimeAnomalyAnalyzer
from app.models.database import SessionLocal
from app.models.entities import Order as DBOrder, SupplierOffer as DBSupplierOffer
from app.rag.schemas import KnowledgeDocument
from app.services.data_service import DataService

logger = logging.getLogger(__name__)


class KnowledgeDocumentBuilder:
    """
    Builds semantic section-based knowledge documents for products, suppliers,
    and cross-functional risks with rich metadata for hybrid semantic retrieval.
    """

    def __init__(self, data_service: DataService | None = None) -> None:
        self.data_service = data_service or DataService()

    def build_all_documents(
        self,
        db: Session | None = None,
    ) -> list[KnowledgeDocument]:
        data = self.data_service.load_data()
        datasets = data.get("datasets", {})

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
            risk_docs = self.build_risk_documents(
                datasets=datasets,
            )
            return product_docs + supplier_docs + risk_docs
        finally:
            if should_close:
                active_db.close()

    def build_product_documents(
        self,
        datasets: dict[str, pd.DataFrame] | None = None,
        db: Session | None = None,
    ) -> list[KnowledgeDocument]:
        if datasets is None:
            data = self.data_service.load_data()
            datasets = data.get("datasets", {})

        products_df = datasets.get("products")
        if products_df is None or products_df.empty:
            return []

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

        sup_analyzer = SupplierRiskAnalyzer()
        try:
            orders_ext = datasets.get("orders_extended")
            if orders_ext is not None and not orders_ext.empty:
                sup_risk_df = sup_analyzer.analyze(orders=orders_ext)
                sup_risk_by_id = (
                    sup_risk_df.set_index("supplier_id").to_dict(orient="index")
                    if not sup_risk_df.empty and "supplier_id" in sup_risk_df.columns
                    else {}
                )
            else:
                sup_risk_by_id = {}
        except Exception as e:
            logger.warning(f"Error computing supplier risk for product docs: {e}")
            sup_risk_by_id = {}

        documents: list[KnowledgeDocument] = []
        for _, prod_row in products_df.iterrows():
            pid = str(prod_row["product_id"]).upper()
            category = str(prod_row.get("category", "General"))
            unit_cost = float(prod_row.get("unit_cost", 0.0))

            sups = suppliers_by_product.get(pid, [])
            sup_ids = [s["supplier_id"] for s in sups]
            if not sup_ids and "supplier_id" in prod_row and pd.notna(prod_row["supplier_id"]):
                fallback_sid = str(prod_row["supplier_id"]).upper()
                sup_ids = [fallback_sid]
                sups = [{"supplier_id": fallback_sid, "supplier_name": fallback_sid}]

            sup_desc = ", ".join(f"{s['supplier_name']} ({s['supplier_id']})" for s in sups) if sups else "Unassigned"

            inv_stats = inv_by_product.get(pid, {})
            avg_inv = float(inv_stats.get("avg_inventory", 0.0))
            zero_inv_days = int(inv_stats.get("zero_inventory_days", 0))
            stockout_rate = float(inv_stats.get("stockout_rate", 0.0))
            days_of_cover = float(inv_stats.get("days_of_cover", 0.0))
            avg_daily_demand = float(inv_stats.get("average_daily_demand", 0.0))
            risk_score = float(inv_stats.get("risk_score", 0.0))
            risk_level = str(inv_stats.get("risk_level", "LOW"))
            risk_reason = str(inv_stats.get("risk_reason", f"Risk score {risk_score:.1f}"))

            sales_stats = sales_by_product.get(pid, {})
            total_demand = float(sales_stats.get("total_demand", avg_daily_demand * 30))
            total_sales = float(sales_stats.get("total_sales", 0.0))

            base_meta = {
                "document_type": "product",
                "entity_id": pid,
                "product_id": pid,
                "product_ids": [pid],
                "supplier_ids": sup_ids,
                "category": category,
                "unit_cost": unit_cost,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "stockout_rate": round(stockout_rate, 4),
                "avg_inventory": round(avg_inv, 2),
                "days_of_cover": round(days_of_cover, 2),
                "total_demand": round(total_demand, 2),
                "source": "product_analytics",
            }

            sup_perf_notes = []
            for s in sups:
                sid_k = s["supplier_id"]
                s_perf = sup_risk_by_id.get(sid_k, {})
                s_lvl = s_perf.get("risk_level", "LOW")
                s_disp = float(s_perf.get("disruption_rate", 0.0)) * 100
                s_late = float(s_perf.get("late_rate", 0.0)) * 100
                sup_perf_notes.append(f"{s['supplier_name']} ({sid_k}: {s_lvl} Risk, {s_disp:.1f}% disruption rate, {s_late:.1f}% late rate)")
            sup_context = "; ".join(sup_perf_notes) if sup_perf_notes else sup_desc

            # Comprehensive Product Document (Operational Risk Profile)
            content_lines = [
                f"Product {pid} Operational Risk Profile ({category}):",
                f"- Category & Unit Cost: Product belongs to {category} category with a standard unit cost of ${unit_cost:.2f}.",
                f"- Supplier Relationships: Sourced from {sup_context}.",
                f"- Inventory Status: Maintains an average inventory of {avg_inv:,.1f} units, providing an estimated {days_of_cover:.1f} days of inventory cover.",
                f"- Stockout Exposure: Recorded {zero_inv_days} zero-inventory stockout days, yielding a stockout frequency of {stockout_rate * 100:.2f}%. Assigned risk level is {risk_level} ({risk_score:.1f}/100) due to {risk_reason}.",
                f"- Demand & Sales: Average daily demand of {avg_daily_demand:.1f} units with total recorded demand of {total_demand:,.0f} units and cumulative sales of ${total_sales:,.2f}.",
            ]
            documents.append(KnowledgeDocument(
                doc_id=f"product:{pid}",
                doc_type="product",
                entity_id=pid,
                title=f"Product {pid} ({category}) Operational Risk Profile",
                content="\n".join(content_lines),
                metadata=base_meta,
            ))

        return documents

    def build_supplier_documents(
        self,
        datasets: dict[str, pd.DataFrame] | None = None,
        db: Session | None = None,
    ) -> list[KnowledgeDocument]:
        if datasets is None:
            data = self.data_service.load_data()
            datasets = data.get("datasets", {})

        suppliers_df = datasets.get("suppliers")
        orders_extended = datasets.get("orders_extended")
        products_df = datasets.get("products")

        if suppliers_df is None or suppliers_df.empty:
            return []

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

        lt_analyzer = LeadTimeAnomalyAnalyzer()
        try:
            if orders_extended is not None and not orders_extended.empty:
                lt_res = lt_analyzer.analyze(orders=orders_extended)
                anom_map = {str(row["supplier_id"]).upper(): row for row in lt_res.get("findings", []) if "supplier_id" in row}
            else:
                anom_map = {}
        except Exception as e:
            logger.warning(f"Error computing lead time anomalies for supplier docs: {e}")
            anom_map = {}

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

        documents: list[KnowledgeDocument] = []
        for _, sup_row in suppliers_df.iterrows():
            sid = str(sup_row["supplier_id"]).upper()
            sname = str(sup_row.get("supplier_name", sup_row.get("name", sid)))
            region = str(sup_row.get("region", "Global"))
            tier = str(sup_row.get("tier", "Standard"))

            prods = products_by_supplier.get(sid, [])
            prod_desc = f"{len(prods)} products (" + ", ".join(prods[:5]) + ("..." if len(prods) > 5 else "") + ")" if prods else "None"

            perf = sup_risk_by_id.get(sid, {})
            total_orders = int(perf.get("total_orders", 0))
            total_units = int(perf.get("total_units", 0))
            late_orders = int(perf.get("late_orders", 0))
            late_rate = float(perf.get("late_rate", 0.0))
            avg_delay = float(perf.get("avg_delay", 0.0))
            avg_lead = float(perf.get("avg_lead_time", 12.0))
            std_lead = float(perf.get("std_lead_time", 3.0))
            disr_rate = float(perf.get("disruption_rate", 0.05))
            risk_score = float(perf.get("risk_score", 20.0))
            risk_level = str(perf.get("risk_level", "LOW"))
            risk_reason = str(perf.get("risk_reason", f"Late rate: {late_rate * 100:.1f}%"))

            anom_data = anom_map.get(sid, {})
            lt_chg_val = anom_data.get("absolute_change_days")
            lt_chg_txt = f", recent lead time change: {lt_chg_val:+.1f}d" if lt_chg_val is not None else ""
            chg_str = f" Recent 90-day lead-time change: {lt_chg_val:+.1f} days ({anom_data.get('percentage_change', 0):+.1f}%), status: {anom_data.get('status', 'Normal')}." if lt_chg_val is not None else ""

            base_meta = {
                "document_type": "supplier",
                "entity_id": sid,
                "supplier_id": sid,
                "supplier_ids": [sid],
                "product_ids": prods,
                "supplier_name": sname,
                "region": region,
                "tier": tier,
                "total_orders": total_orders,
                "total_units": total_units,
                "late_rate": round(late_rate, 4),
                "avg_delay": round(avg_delay, 2),
                "avg_lead_time": round(avg_lead, 1),
                "std_lead_time": round(std_lead, 1),
                "disruption_rate": round(disr_rate, 4),
                "risk_score": risk_score,
                "risk_level": risk_level,
                "source": "supplier_analytics",
            }

            content_lines = [
                f"Supplier {sid} ({sname}) Performance & Relationship Profile:",
                f"- Region & Classification: Operating in {region} as a Tier {tier} supplier.",
                f"- Products Supplied: Supplies {prod_desc}.",
                f"- Delivery Reliability: {total_orders:,} total orders executed with {total_units:,} units delivered. {late_orders:,} late orders resulting in a late delivery rate of {late_rate * 100:.2f}% (average delay: {avg_delay:.1f} days).",
                f"- Lead-Time Behavior: Average fulfillment lead time {avg_lead:.1f} days (std: {std_lead:.1f}d){lt_chg_txt}.{chg_str}",
                f"- Disruption History: Recorded disruption rate of {disr_rate * 100:.1f}% across historical orders, impacting fulfillment continuity for supplied products ({prod_desc}).",
                f"- Supplier Risk Assessment: Score {risk_score:.1f}/100 categorized as {risk_level} Risk. Details: {risk_reason}.",
            ]

            documents.append(KnowledgeDocument(
                doc_id=f"supplier:{sid}",
                doc_type="supplier",
                entity_id=sid,
                title=f"Supplier {sid} ({sname}) Performance & Relationship Profile",
                content="\n".join(content_lines),
                metadata=base_meta,
            ))

        return documents

    def build_risk_documents(
        self,
        datasets: dict[str, pd.DataFrame] | None = None,
    ) -> list[KnowledgeDocument]:
        """
        Creates semantic documents describing supply chain risk definitions,
        operational metrics, and standard mitigation procedures.
        """
        risk_definitions = [
            {
                "topic": "supplier_delivery_risk",
                "title": "Supplier Delivery Risk Framework",
                "content": (
                    "Supplier delivery risk evaluates the probability and impact of fulfillment delays. "
                    "Key supporting metrics include late-delivery rate, average delay days, lead-time standard deviation, "
                    "and volume exposure. High delivery risk creates inventory depletion and downstream production bottlenecks. "
                    "Mitigation includes dual-sourcing, dynamic lead-time buffers, and targeted vendor recovery plans."
                ),
            },
            {
                "topic": "lead_time_anomalies",
                "title": "Lead-Time Anomaly Detection Framework",
                "content": (
                    "Lead-time anomalies represent sudden statistically significant deviations in supplier fulfillment duration "
                    "relative to historical baselines. Calculated using recent 90-day moving averages compared to historical averages, "
                    "evaluated via percentage change and z-scores. A surge in lead time signals underlying manufacturing or logistical friction. "
                    "Mitigation requires safety-stock adjustments and proactive supplier dispatch tracking."
                ),
            },
            {
                "topic": "disruption_risk",
                "title": "Supplier Disruption Impact Framework",
                "content": (
                    "Disruption impact analysis traces supplier failure modes through dependent products, demand velocity, "
                    "current inventory reserves, and stockout probabilities. When a high-disruption supplier feeds critical SKUs with low "
                    "days-of-cover, stockout probability escalates rapidly. Mitigation involves strategic buffering and pre-qualifying backup suppliers."
                ),
            },
            {
                "topic": "inventory_stockout_risk",
                "title": "Inventory Availability and Stockout Risk Framework",
                "content": (
                    "Inventory risk measures the likelihood that product stock is exhausted before replenish orders arrive. "
                    "Key metrics include stockout rate, days of inventory cover, and demand pressure. Days of cover under 7 days "
                    "is considered critical exposure. Mitigation includes expedited replenishment orders and dynamic reorder threshold adjustments."
                ),
            },
            {
                "topic": "route_logistics_risk",
                "title": "Transportation and Route Risk Framework",
                "content": (
                    "Logistics route risk evaluates delay exposure and transit volatility across shipping corridors and 3PL partners. "
                    "High delay rates and route disruptions jeopardize scheduled replenishment. Mitigation involves carrier re-allocation "
                    "and contingency transit scheduling."
                ),
            },
        ]

        documents: list[KnowledgeDocument] = []
        for r in risk_definitions:
            documents.append(KnowledgeDocument(
                doc_id=f"risk:{r['topic']}",
                doc_type="risk",
                entity_id=r["topic"],
                title=r["title"],
                content=r["content"],
                metadata={
                    "document_type": "risk",
                    "topic": r["topic"],
                    "risk_level": "GENERAL",
                    "source": "risk_intelligence",
                },
            ))

        return documents
