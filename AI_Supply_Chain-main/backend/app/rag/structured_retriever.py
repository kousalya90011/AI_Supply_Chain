from __future__ import annotations

import logging
from typing import Any
import pandas as pd
from sqlalchemy.orm import Session

from app.models.database import SessionLocal
from app.models.entities import Order as DBOrder, SupplierOffer as DBSupplierOffer
from app.query.factory import create_analytics_registry
from app.query.schema import QueryPlan
from app.query.scope import QueryScope, supplier_ids_match
from app.rag.schemas import EvidenceItem, RetrievalResult

logger = logging.getLogger(__name__)


class StructuredRetriever:
    """
    Performs precise structured retrieval for exact metrics, counts, and entity relationships
    from SQL tables and deterministic warehouse analytics.
    """

    def __init__(self, registry: Any = None) -> None:
        self.registry = registry or create_analytics_registry()

    def retrieve(
        self,
        plan: QueryPlan,
        user_scope: QueryScope | None = None,
        db: Session | None = None,
    ) -> RetrievalResult:
        """
        Executes structured analytics and DB queries, returning standardized EvidenceItem objects.
        """
        evidence_items: list[dict[str, Any]] = []
        sources: set[str] = set()

        metric = plan.metric
        entity = plan.entity or "unknown"
        entity_id = plan.entity_id

        # -----------------------------------------------------
        # 1. Deterministic Analytics Execution via Registry
        # -----------------------------------------------------
        if metric and self.registry.is_registered(metric):
            try:
                adapter = self.registry.get(metric)
                res = adapter.execute(plan)
                findings = res.get("findings", [])
                raw_evidence = res.get("evidence", [])

                sources.add(f"Analytics ({metric})")

                # Format findings as structured EvidenceItems
                for item in findings:
                    if not isinstance(item, dict):
                        continue

                    # Extract primary value and metric description
                    val = (
                        item.get(metric)
                        if metric in item
                        else item.get("value")
                    )
                    if val is None:
                        # Fallback to first non-id numeric or descriptive key
                        for k, v in item.items():
                            if k not in {"product_id", "supplier_id", "index", "id"}:
                                val = v
                                break

                    e_type = "supplier" if "supplier_id" in item and entity == "supplier" else "product"
                    e_id = item.get("supplier_id") if e_type == "supplier" else item.get("product_id", entity_id)

                    ev = EvidenceItem(
                        source_type="analytics",
                        source_id=f"analytics:{metric}",
                        entity_type=e_type,
                        entity_id=e_id,
                        metric=metric,
                        value=val,
                        explanation=f"{metric} for {e_type} {e_id}: {val}",
                        retrieval_method="structured",
                        confidence=1.0,
                    )
                    evidence_items.append(ev.to_dict())

                # If raw evidence exists, also include it
                for ev_raw in raw_evidence:
                    if isinstance(ev_raw, dict):
                        ev_data = ev_raw.get("data", ev_raw)
                        evidence_items.append({
                            "source_type": "analytics",
                            "source_id": f"dataset:{ev_raw.get('dataset', 'warehouse')}",
                            "entity_type": entity,
                            "entity_id": entity_id,
                            "metric": metric,
                            "value": ev_data,
                            "explanation": f"Operational record for {entity} {entity_id}",
                            "retrieval_method": "structured",
                            "confidence": 1.0,
                        })

            except Exception as e:
                logger.warning(f"Error during structured analytics retrieval: {e}")

        # -----------------------------------------------------
        # 2. Live Database Queries (Supplier Offers & Orders)
        # -----------------------------------------------------
        should_close = False
        active_db = db
        if active_db is None:
            active_db = SessionLocal()
            should_close = True

        try:
            # Query active supplier offers
            if metric in {"supplier_offers", "offers"} or "offer" in (plan.original_query or "").lower():
                sources.add("Transactional Database (Supplier Offers)")
                query_filter = active_db.query(DBSupplierOffer)
                if user_scope and getattr(user_scope, "is_supplier", False):
                    query_filter = query_filter.filter(
                        DBSupplierOffer.supplier_id == user_scope.supplier_id
                    )
                elif entity_id and (entity == "supplier" or str(entity_id).startswith("S")):
                    query_filter = query_filter.filter(
                        DBSupplierOffer.supplier_id == entity_id
                    )
                elif entity_id and (entity == "product" or str(entity_id).startswith("P")):
                    query_filter = query_filter.filter(
                        DBSupplierOffer.product_id == entity_id
                    )

                offers = query_filter.limit(20).all()
                for off in offers:
                    ev = EvidenceItem(
                        source_type="database",
                        source_id=f"supplier_offer:{off.offer_id}",
                        entity_type="offer",
                        entity_id=str(off.offer_id),
                        metric="offer_details",
                        value={
                            "offer_id": off.offer_id,
                            "supplier_id": off.supplier_id,
                            "product_id": off.product_id,
                            "price": off.unit_price,
                            "quantity": off.quantity,
                            "status": off.status,
                            "delivery_days": off.delivery_days,
                        },
                        explanation=(
                            f"Offer #{off.offer_id} from {off.supplier_id} for product {off.product_id}: "
                            f"${off.unit_price:.2f} ({off.status})"
                        ),
                        retrieval_method="structured",
                        confidence=1.0,
                    )
                    evidence_items.append(ev.to_dict())

            # Query live orders if applicable
            if metric in {"orders", "total_orders"} or "order" in (plan.original_query or "").lower():
                sources.add("Transactional Database (Orders)")
                order_query = active_db.query(DBOrder)
                if user_scope and getattr(user_scope, "is_supplier", False):
                    order_query = order_query.filter(
                        DBOrder.supplier_id == user_scope.supplier_id
                    )
                elif entity_id and (entity == "supplier" or str(entity_id).startswith("S")):
                    order_query = order_query.filter(
                        DBOrder.supplier_id == entity_id
                    )
                elif entity_id and (entity == "product" or str(entity_id).startswith("P")):
                    order_query = order_query.filter(
                        DBOrder.product_id == entity_id
                    )

                orders = order_query.limit(20).all()
                for o in orders:
                    ev = EvidenceItem(
                        source_type="database",
                        source_id=f"order:{o.order_id}",
                        entity_type="order",
                        entity_id=str(o.order_id),
                        metric="order_details",
                        value={
                            "order_id": o.order_id,
                            "product_id": o.product_id,
                            "supplier_id": o.supplier_id,
                            "quantity": o.quantity,
                            "unit_price": o.unit_price,
                            "status": getattr(o, "status", "CONFIRMED"),
                        },
                        explanation=f"Order #{o.order_id}: {o.quantity} units of {o.product_id} from {o.supplier_id}",
                        retrieval_method="structured",
                        confidence=1.0,
                    )
                    evidence_items.append(ev.to_dict())

        except Exception as e:
            logger.warning(f"Error querying transactional DB: {e}")
        finally:
            if should_close:
                active_db.close()

        return RetrievalResult(
            retrieval_mode="structured",
            evidence=evidence_items,
            documents=[],
            sources=sorted(sources),
        )
