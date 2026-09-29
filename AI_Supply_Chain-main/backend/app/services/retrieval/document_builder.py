from __future__ import annotations

import logging
from typing import Any
import pandas as pd
from sqlalchemy.orm import Session

from app.analytics.inventory_risk import InventoryRiskAnalyzer
from app.analytics.supplier_risk import SupplierRiskAnalyzer
from app.analytics.lead_time_anomaly import LeadTimeAnomalyAnalyzer
from app.models.database import SessionLocal
from app.services.data_service import DataService
from app.services.retrieval.chunking import BusinessChunkingService
from app.services.retrieval.retrieval_models import BusinessChunk

logger = logging.getLogger(__name__)


class KnowledgeDocumentBuilder:
    """
    Constructs business-level knowledge documents and chunks from
    operational datasets and deterministic analytics.
    """

    def __init__(self, data_service: DataService | None = None) -> None:
        self.data_service = data_service or DataService()

    def build_all_chunks(self, db: Session | None = None) -> list[BusinessChunk]:
        """
        Runs analytics and generates the complete suite of business-level chunks.
        """
        data = self.data_service.load_data()
        datasets = data.get("datasets", {})

        should_close = False
        active_db = db
        if active_db is None:
            active_db = SessionLocal()
            should_close = True

        try:
            supplier_chunks = self.build_supplier_chunks(datasets=datasets)
            inventory_chunks = self.build_inventory_chunks(datasets=datasets)
            route_chunks = self.build_route_chunks(datasets=datasets)
            disruption_chunks = self.build_disruption_chunks(datasets=datasets)
            knowledge_chunks = BusinessChunkingService.create_knowledge_chunks()

            all_chunks = (
                supplier_chunks
                + inventory_chunks
                + route_chunks
                + disruption_chunks
                + knowledge_chunks
            )
            logger.info(f"Built {len(all_chunks)} total business-level knowledge chunks.")
            return all_chunks
        finally:
            if should_close and active_db is not None:
                active_db.close()

    def build_supplier_chunks(
        self,
        datasets: dict[str, pd.DataFrame] | None = None,
    ) -> list[BusinessChunk]:
        """
        Generates semantic supplier risk profile chunks.
        """
        if datasets is None:
            datasets = self.data_service.load_data().get("datasets", {})

        suppliers_df = datasets.get("suppliers")
        orders_df = datasets.get("orders_extended")
        if suppliers_df is None or suppliers_df.empty:
            return []

        # Run supplier risk analytics
        risk_map: dict[str, dict[str, Any]] = {}
        try:
            analyzer = SupplierRiskAnalyzer()
            risk_df = analyzer.analyze(
                orders=orders_df,
            )
            if not risk_df.empty and "supplier_id" in risk_df.columns:
                risk_map = risk_df.set_index("supplier_id").to_dict(orient="index")
        except Exception as e:
            logger.warning(f"Error computing supplier risk analytics: {e}")

        # Check lead time anomalies
        anomaly_sids: set[str] = set()
        try:
            lt_analyzer = LeadTimeAnomalyAnalyzer()
            anomaly_res = lt_analyzer.analyze(orders=orders_df)
            anomalies_df = anomaly_res.get("anomalies")
            if anomalies_df is not None and hasattr(anomalies_df, "columns") and "supplier_id" in anomalies_df.columns:
                anomaly_sids = set(anomalies_df["supplier_id"].astype(str).str.upper())
        except Exception as e:
            logger.warning(f"Error computing lead time anomalies: {e}")

        chunks: list[BusinessChunk] = []
        for _, row in suppliers_df.iterrows():
            sid = str(row.get("supplier_id", "")).strip().upper()
            if not sid:
                continue

            r_info = risk_map.get(sid, {})
            risk_score = float(r_info.get("composite_risk_score", row.get("risk_score", 30.0)))
            risk_level = str(r_info.get("risk_level", "NORMAL")).upper()

            total_orders = int(r_info.get("total_orders", 0))
            late_orders = int(r_info.get("late_orders", 0))
            late_rate = float(r_info.get("late_rate", 0.0))
            avg_delay = float(r_info.get("avg_delay_days", 0.0))
            lead_time = float(r_info.get("avg_lead_time", row.get("lead_time_days", 5.0)))

            chunk = BusinessChunkingService.create_supplier_chunk(
                supplier_id=sid,
                supplier_name=str(row.get("supplier_name", sid)),
                risk_score=risk_score,
                risk_level=risk_level,
                total_orders=total_orders,
                late_orders=late_orders,
                late_rate=late_rate,
                avg_delay_days=avg_delay,
                lead_time_days=lead_time,
                lead_time_anomaly=(sid in anomaly_sids),
                city=str(row.get("city", "")),
            )
            chunks.append(chunk)

        return chunks

    def build_inventory_chunks(
        self,
        datasets: dict[str, pd.DataFrame] | None = None,
    ) -> list[BusinessChunk]:
        """
        Generates semantic inventory and product risk profile chunks.
        """
        if datasets is None:
            datasets = self.data_service.load_data().get("datasets", {})

        products_df = datasets.get("products")
        if products_df is None or products_df.empty:
            return []

        inv_map: dict[str, dict[str, Any]] = {}
        try:
            inv_analyzer = InventoryRiskAnalyzer(self.data_service)
            inv_df = inv_analyzer.analyze()
            if not inv_df.empty and "product_id" in inv_df.columns:
                inv_map = inv_df.set_index("product_id").to_dict(orient="index")
        except Exception as e:
            logger.warning(f"Error computing inventory risk analytics: {e}")

        chunks: list[BusinessChunk] = []
        for _, row in products_df.iterrows():
            pid = str(row.get("product_id", "")).strip().upper()
            if not pid:
                continue

            inv_info = inv_map.get(pid, {})
            risk_score = float(inv_info.get("inventory_risk_score", 25.0))
            risk_level = str(inv_info.get("risk_level", "NORMAL")).upper()

            avg_inv = float(inv_info.get("avg_inventory", 50.0))
            daily_demand = float(inv_info.get("avg_daily_demand", 10.0))
            doc = float(inv_info.get("days_of_cover", 15.0))
            stockout_rate = float(inv_info.get("stockout_rate", 0.0))
            demand_pressure = float(inv_info.get("demand_pressure", 20.0))

            chunk = BusinessChunkingService.create_inventory_chunk(
                product_id=pid,
                product_name=str(row.get("product_name", pid)),
                category=str(row.get("category", "General")),
                risk_score=risk_score,
                risk_level=risk_level,
                avg_inventory=avg_inv,
                avg_daily_demand=daily_demand,
                days_of_cover=doc,
                stockout_rate=stockout_rate,
                demand_pressure=demand_pressure,
                supplier_ids=[str(row.get("supplier_id"))] if pd.notna(row.get("supplier_id")) else [],
            )
            chunks.append(chunk)

        return chunks

    def build_route_chunks(
        self,
        datasets: dict[str, pd.DataFrame] | None = None,
    ) -> list[BusinessChunk]:
        """
        Generates route risk profile chunks.
        """
        if datasets is None:
            datasets = self.data_service.load_data().get("datasets", {})

        routes_df = datasets.get("routes")
        if routes_df is None or routes_df.empty:
            return []

        chunks: list[BusinessChunk] = []
        for _, row in routes_df.iterrows():
            rid = str(row.get("route_id", "")).strip().upper()
            if not rid:
                continue

            risk_score = float(row.get("risk_score", row.get("route_risk_score", 20.0)))
            risk_level = "HIGH" if risk_score > 60 else ("MEDIUM" if risk_score > 35 else "LOW")
            origin = str(row.get("origin", "Origin"))
            destination = str(row.get("destination", "Destination"))

            chunk = BusinessChunkingService.create_route_chunk(
                route_id=rid,
                origin=origin,
                destination=destination,
                risk_score=risk_score,
                risk_level=risk_level,
                avg_delay_days=float(row.get("avg_delay_days", 0.5)),
                transit_time_days=float(row.get("transit_time_days", 2.0)),
            )
            chunks.append(chunk)

        return chunks

    def build_disruption_chunks(
        self,
        datasets: dict[str, pd.DataFrame] | None = None,
    ) -> list[BusinessChunk]:
        """
        Generates disruption event profile chunks.
        """
        if datasets is None:
            datasets = self.data_service.load_data().get("datasets", {})

        disruptions_df = datasets.get("disruptions")
        if disruptions_df is None or disruptions_df.empty:
            return []

        chunks: list[BusinessChunk] = []
        for _, row in disruptions_df.iterrows():
            did = str(row.get("disruption_id", "")).strip().upper()
            if not did:
                continue

            event_type = str(row.get("event_type", "Operational Disruption"))
            severity = str(row.get("severity", "MEDIUM")).upper()
            description = str(row.get("description", f"Disruption logged on corridor {row.get('route_id')}"))
            impact_days = int(row.get("impact_duration_days", row.get("duration_days", 1)))

            chunk = BusinessChunkingService.create_disruption_chunk(
                disruption_id=did,
                route_id=str(row.get("route_id", "")),
                event_type=event_type,
                severity=severity,
                description=description,
                impact_duration_days=impact_days,
                start_date=str(row.get("start_date", "")),
            )
            chunks.append(chunk)

        return chunks
