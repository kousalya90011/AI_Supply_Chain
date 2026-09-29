from __future__ import annotations

import logging
from typing import Any
import pandas as pd

from app.services.retrieval.retrieval_models import BusinessChunk

logger = logging.getLogger(__name__)


class BusinessChunkingService:
    """
    Transforms structured records, operational analytics, and system rules
    into business-level semantic knowledge chunks.

    Guarantees:
    - NO raw CSV row chunking (prevents 200,000 raw embeddings explosion).
    - Domain-aligned business profiles (Supplier, Inventory, Route, Disruption, Methodology).
    - Deterministic, reproducible chunk IDs.
    - Rich metadata for strict RBAC pre-filtering and provenance auditability.
    """

    # -------------------------------------------------------------
    # 1. SUPPLIER RISK CHUNK
    # -------------------------------------------------------------
    @classmethod
    def create_supplier_chunk(
        cls,
        *,
        supplier_id: str,
        supplier_name: str | None = None,
        risk_score: float,
        risk_level: str,
        total_orders: int,
        late_orders: int,
        late_rate: float,
        avg_delay_days: float,
        lead_time_days: float | None = None,
        lead_time_anomaly: bool = False,
        primary_routes: list[str] | None = None,
        associated_products: list[str] | None = None,
        city: str | None = None,
    ) -> BusinessChunk:
        """
        Creates a structured, human-readable supplier risk profile chunk.
        """
        clean_sid = str(supplier_id).strip().upper()
        clean_level = str(risk_level).strip().upper()

        risk_factors: list[str] = []
        if late_rate > 15.0 or clean_level in {"HIGH", "CRITICAL"}:
            risk_factors.append(f"Elevated delivery delay rate ({late_rate:.1f}%)")
        if avg_delay_days > 3.0:
            risk_factors.append(f"Significant transit delay averaging {avg_delay_days:.1f} days")
        if lead_time_anomaly:
            risk_factors.append("Detected statistical lead-time shift/anomaly vs historical baseline")
        if not risk_factors:
            risk_factors.append("Nominal operational telemetry; reliable on-time fulfillment")

        recommendations: list[str] = []
        if clean_level in {"HIGH", "CRITICAL"}:
            recommendations.append("Initiate active SLA review and monitor weekly delivery variance.")
            recommendations.append("Identify secondary backup suppliers for critical component stock.")
        else:
            recommendations.append("Maintain standard operational cadence and performance monitoring.")

        content_lines = [
            "### Supplier Risk Profile",
            f"Supplier ID: {clean_sid}",
            f"Supplier Name: {supplier_name or clean_sid}",
            f"Overall Risk Score: {risk_score:.1f}",
            f"Risk Level: {clean_level}",
            "",
            "Delivery Performance:",
            f"- Total Orders: {total_orders}",
            f"- Late Orders: {late_orders}",
            f"- Late Rate: {late_rate:.1f}%",
            f"- Average Delay: {avg_delay_days:.1f} days",
        ]
        if lead_time_days is not None:
            content_lines.append(f"- Average Lead Time: {lead_time_days:.1f} days")
        content_lines.extend([
            "",
            "Risk Factors:",
            *[f"- {rf}" for rf in risk_factors],
            "",
            "Recommended Monitoring:",
            *[f"- {rec}" for rec in recommendations],
        ])

        chunk_id = f"supplier_{clean_sid}_risk"
        metadata = {
            "supplier_id": clean_sid,
            "supplier_name": supplier_name or clean_sid,
            "risk_score": float(risk_score),
            "risk_level": clean_level,
            "total_orders": int(total_orders),
            "late_rate": float(late_rate),
            "avg_delay_days": float(avg_delay_days),
            "associated_products": associated_products or [],
            "primary_routes": primary_routes or [],
            "city": city or "",
            "topic": "supplier_risk",
        }

        return BusinessChunk(
            chunk_id=chunk_id,
            document_type="supplier_risk_profile",
            entity_type="supplier",
            entity_id=clean_sid,
            title=f"Supplier Risk Profile: {clean_sid}",
            content="\n".join(content_lines),
            source="supplier_risk_analytics",
            risk_level=clean_level,
            metadata=metadata,
        )

    # -------------------------------------------------------------
    # 2. INVENTORY / PRODUCT RISK CHUNK
    # -------------------------------------------------------------
    @classmethod
    def create_inventory_chunk(
        cls,
        *,
        product_id: str,
        product_name: str | None = None,
        category: str | None = None,
        risk_score: float,
        risk_level: str,
        avg_inventory: float,
        avg_daily_demand: float,
        days_of_cover: float,
        stockout_rate: float,
        demand_pressure: float,
        supplier_ids: list[str] | None = None,
    ) -> BusinessChunk:
        """
        Creates a structured, human-readable inventory & product risk profile chunk.
        """
        clean_pid = str(product_id).strip().upper()
        clean_level = str(risk_level).strip().upper()

        risk_drivers: list[str] = []
        if days_of_cover < 3.0:
            risk_drivers.append(f"Depleted days of cover runway ({days_of_cover:.2f} days)")
        if stockout_rate > 20.0:
            risk_drivers.append(f"High historical stockout frequency ({stockout_rate:.1f}%)")
        if demand_pressure > 70.0:
            risk_drivers.append(f"Elevated demand pressure index ({demand_pressure:.1f}%)")
        if not risk_drivers:
            risk_drivers.append("Sufficient inventory buffer and balanced demand distribution")

        content_lines = [
            "### Inventory Risk Profile",
            f"Product ID: {clean_pid}",
            f"Product Name: {product_name or clean_pid}",
            f"Category: {category or 'General'}",
            f"Risk Score: {risk_score:.2f}",
            f"Risk Level: {clean_level}",
            "",
            "Operational Metrics:",
            f"- Average Inventory: {avg_inventory:.1f} units",
            f"- Average Daily Demand: {avg_daily_demand:.2f} units/day",
            f"- Days of Cover: {days_of_cover:.2f} days",
            f"- Stockout Rate: {stockout_rate:.2f}%",
            f"- Demand Pressure: {demand_pressure:.2f}%",
            "",
            "Risk Drivers:",
            *[f"- {rd}" for rd in risk_drivers],
            "",
            "Associated Suppliers:",
            f"- {', '.join(supplier_ids) if supplier_ids else 'Unassigned'}",
        ]

        chunk_id = f"product_{clean_pid}_inventory"
        metadata = {
            "product_id": clean_pid,
            "product_name": product_name or clean_pid,
            "category": category or "",
            "risk_score": float(risk_score),
            "risk_level": clean_level,
            "days_of_cover": float(days_of_cover),
            "stockout_rate": float(stockout_rate),
            "supplier_ids": supplier_ids or [],
            "topic": "inventory_risk",
        }

        return BusinessChunk(
            chunk_id=chunk_id,
            document_type="inventory_risk_profile",
            entity_type="product",
            entity_id=clean_pid,
            title=f"Inventory Risk Profile: {clean_pid}",
            content="\n".join(content_lines),
            source="inventory_risk_analytics",
            risk_level=clean_level,
            metadata=metadata,
        )

    # -------------------------------------------------------------
    # 3. ROUTE RISK CHUNK
    # -------------------------------------------------------------
    @classmethod
    def create_route_chunk(
        cls,
        *,
        route_id: str,
        origin: str,
        destination: str,
        risk_score: float,
        risk_level: str,
        avg_delay_days: float = 0.0,
        disruption_count: int = 0,
        transit_time_days: float = 0.0,
        primary_carriers: list[str] | None = None,
    ) -> BusinessChunk:
        """
        Creates a structured route logistics and disruption profile chunk.
        """
        clean_rid = str(route_id).strip().upper()
        clean_level = str(risk_level).strip().upper()

        risk_factors: list[str] = []
        if avg_delay_days > 2.0:
            risk_factors.append(f"Transit delivery delays averaging {avg_delay_days:.1f} days")
        if disruption_count > 0:
            risk_factors.append(f"Historical disruption exposure ({disruption_count} logged incidents)")
        if not risk_factors:
            risk_factors.append("Reliable corridor performance and stable carrier transit")

        content_lines = [
            "### Route Risk Profile",
            f"Route ID: {clean_rid}",
            f"Origin: {origin}",
            f"Destination: {destination}",
            f"Risk Score: {risk_score:.2f}",
            f"Risk Level: {clean_level}",
            "",
            "Corridor Telemetry:",
            f"- Average Delay: {avg_delay_days:.1f} days",
            f"- Disruption Incidents: {disruption_count}",
            f"- Baseline Transit Time: {transit_time_days:.1f} days",
            f"- Primary Carriers / 3PL: {', '.join(primary_carriers) if primary_carriers else 'Standard'}",
            "",
            "Risk Factors:",
            *[f"- {rf}" for rf in risk_factors],
        ]

        chunk_id = f"route_{clean_rid}_risk"
        metadata = {
            "route_id": clean_rid,
            "origin": origin,
            "destination": destination,
            "risk_score": float(risk_score),
            "risk_level": clean_level,
            "disruption_count": int(disruption_count),
            "topic": "route_risk",
        }

        return BusinessChunk(
            chunk_id=chunk_id,
            document_type="route_risk_profile",
            entity_type="route",
            entity_id=clean_rid,
            title=f"Route Risk Profile: {origin} to {destination} ({clean_rid})",
            content="\n".join(content_lines),
            source="route_risk_analytics",
            risk_level=clean_level,
            metadata=metadata,
        )

    # -------------------------------------------------------------
    # 4. DISRUPTION EVENT CHUNK
    # -------------------------------------------------------------
    @classmethod
    def create_disruption_chunk(
        cls,
        *,
        disruption_id: str,
        route_id: str | None = None,
        event_type: str,
        severity: str,
        description: str,
        impact_duration_days: int = 0,
        start_date: str | None = None,
    ) -> BusinessChunk:
        """
        Creates a disruption event profile chunk.
        """
        clean_did = str(disruption_id).strip().upper()
        clean_sev = str(severity).strip().upper()

        content_lines = [
            "### Supply Chain Disruption Event",
            f"Disruption ID: {clean_did}",
            f"Event Type: {event_type}",
            f"Severity: {clean_sev}",
            f"Corridor / Route ID: {route_id or 'Network-wide'}",
            f"Impact Duration: {impact_duration_days} days",
            f"Logged Date: {start_date or 'Historical'}",
            "",
            "Impact Narrative:",
            f"{description}",
        ]

        chunk_id = f"disruption_{clean_did}"
        metadata = {
            "disruption_id": clean_did,
            "route_id": route_id or "",
            "event_type": event_type,
            "severity": clean_sev,
            "impact_duration_days": int(impact_duration_days),
            "topic": "disruption_event",
        }

        return BusinessChunk(
            chunk_id=chunk_id,
            document_type="disruption_profile",
            entity_type="disruption",
            entity_id=clean_did,
            title=f"Disruption Event: {event_type} ({clean_did})",
            content="\n".join(content_lines),
            source="disruption_telemetry",
            risk_level=clean_sev,
            metadata=metadata,
        )

    # -------------------------------------------------------------
    # 5. GENERAL METHODOLOGY & RISK RULES CHUNKS
    # -------------------------------------------------------------
    @classmethod
    def create_knowledge_chunks(cls) -> list[BusinessChunk]:
        """
        Creates static business rules, threshold definitions, and methodology chunks.
        """
        chunks = [
            BusinessChunk(
                chunk_id="knowledge_risk_scoring_methodology",
                document_type="methodology_guide",
                entity_type="knowledge",
                entity_id="methodology_risk",
                title="Risk Scoring Methodology and Weighting Framework",
                content=(
                    "### Risk Scoring Framework\n"
                    "The Supply Chain Control Tower evaluates risk across composite dimensions:\n"
                    "- Delivery Delay Weight: 40% (measures late rate and average days delayed)\n"
                    "- Route Volatility Weight: 20% (measures corridor disruptions and carrier delays)\n"
                    "- Unit Volume Impact: 20% (scales risk with exposure volume)\n"
                    "- Unit Cost Exposure: 10% (evaluates financial value at risk)\n"
                    "- Handling Complexity: 10% (specialized freight and storage constraints)\n"
                    "Composite scores range from 0 (minimal risk) to 100 (critical disruption threat)."
                ),
                source="control_tower_architecture",
                risk_level="NORMAL",
                metadata={"topic": "methodology", "scope": "global"},
            ),
            BusinessChunk(
                chunk_id="knowledge_inventory_runway_thresholds",
                document_type="methodology_guide",
                entity_type="knowledge",
                entity_id="methodology_inventory",
                title="Inventory Days of Cover and Stockout Thresholds",
                content=(
                    "### Inventory Health Thresholds\n"
                    "- CRITICAL: Days of cover < 2.0 days or stockout rate > 30%.\n"
                    "- HIGH RISK: Days of cover between 2.0 and 5.0 days with demand pressure > 60%.\n"
                    "- MEDIUM: Days of cover between 5.0 and 14.0 days.\n"
                    "- HEALTHY: Days of cover >= 14.0 days with zero stockouts.\n"
                    "Inventory replenishment lead times must always remain shorter than days of cover runway."
                ),
                source="control_tower_architecture",
                risk_level="NORMAL",
                metadata={"topic": "inventory_thresholds", "scope": "global"},
            ),
            BusinessChunk(
                chunk_id="knowledge_dataset_provenance",
                document_type="system_documentation",
                entity_type="knowledge",
                entity_id="dataset_provenance",
                title="Dataset Provenance and Architecture Specification",
                content=(
                    "### Synthetic Supply Chain Risk Intelligence Dataset\n"
                    "Designed to preserve enterprise-scale order/logistics structure while adding clearly "
                    "identified synthetic extensions required for supplier reliability analysis, inventory stockout "
                    "runway forecasting, and lead-time anomaly detection."
                ),
                source="control_tower_architecture",
                risk_level="NORMAL",
                metadata={"topic": "provenance", "scope": "global"},
            ),
        ]
        return chunks
