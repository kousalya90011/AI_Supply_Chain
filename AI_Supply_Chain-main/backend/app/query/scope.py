from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any
import pandas as pd
from sqlalchemy.orm import Session

from app.models.database import SessionLocal
from app.models.entities import Order, Product, SupplierOffer, User, UserRole


def normalize_supplier_id(sid: str | None) -> str | None:
    if not sid:
        return None
    s = str(sid).strip().upper()
    match = re.match(r"^S0*(\d+)$", s)
    if match:
        return f"S{match.group(1)}"
    return s


def supplier_ids_match(sid1: str | None, sid2: str | None) -> bool:
    if not sid1 or not sid2:
        return False
    s1 = str(sid1).strip().upper()
    s2 = str(sid2).strip().upper()
    if s1 == s2:
        return True
    n1 = normalize_supplier_id(s1)
    n2 = normalize_supplier_id(s2)
    return n1 is not None and n1 == n2


@dataclass
class QueryScope:
    username: str
    role: str
    supplier_id: str | None = None
    scope_type: str = "GLOBAL"  # "GLOBAL", "GLOBAL_OPERATIONAL", "SUPPLIER_ONLY"

    def __post_init__(self) -> None:
        role_str = str(self.role.value if hasattr(self.role, "value") else self.role).upper()
        if (role_str == "SUPPLIER" or "SUPPLIER" in role_str) and self.scope_type == "GLOBAL":
            self.scope_type = "SUPPLIER_ONLY"

    @classmethod
    def from_user(cls, user: User) -> QueryScope:
        role = getattr(user, "role", UserRole.ADMIN)
        if hasattr(role, "value"):
            role = role.value
        role_str = str(role).upper()

        if role_str == UserRole.ADMIN.value:
            scope_type = "GLOBAL"
        elif role_str == UserRole.SUPPLY_CHAIN_MANAGER.value:
            scope_type = "GLOBAL_OPERATIONAL"
        elif role_str == UserRole.SUPPLIER.value:
            scope_type = "SUPPLIER_ONLY"
        else:
            scope_type = "SUPPLIER_ONLY"

        return cls(
            username=user.username,
            role=role_str,
            supplier_id=user.supplier_id,
            scope_type=scope_type,
        )

    @property
    def is_global(self) -> bool:
        return self.scope_type in {"GLOBAL", "GLOBAL_OPERATIONAL"}

    @property
    def is_supplier(self) -> bool:
        return self.scope_type == "SUPPLIER_ONLY"


def get_supplier_authorized_products(
    supplier_id: str,
    datasets: dict[str, pd.DataFrame] | None = None,
    db: Session | None = None,
) -> set[str]:
    """
    Determine all product IDs supplied by the given supplier.
    Sources:
    1. CSV datasets: products, orders_extended
    2. SQL database: orders, supplier_offers, products
    """
    if not supplier_id:
        return set()

    target_sid = str(supplier_id).strip().upper()
    norm_target = normalize_supplier_id(target_sid)
    authorized_products: set[str] = set()

    # 1. Check datasets if available
    if datasets:
        products_df = datasets.get("products")
        if products_df is not None and not products_df.empty:
            if "supplier_id" in products_df.columns and "product_id" in products_df.columns:
                for _, row in products_df.iterrows():
                    row_sid = str(row["supplier_id"]).strip().upper()
                    if row_sid == target_sid or normalize_supplier_id(row_sid) == norm_target:
                        authorized_products.add(str(row["product_id"]).strip().upper())

        orders_df = datasets.get("orders_extended")
        if orders_df is not None and not orders_df.empty:
            if "supplier_id" in orders_df.columns and "product_id" in orders_df.columns:
                for _, row in orders_df.iterrows():
                    row_sid = str(row["supplier_id"]).strip().upper()
                    if row_sid == target_sid or normalize_supplier_id(row_sid) == norm_target:
                        authorized_products.add(str(row["product_id"]).strip().upper())

    # 2. Check SQL DB
    should_close = False
    active_db = db
    if active_db is None:
        active_db = SessionLocal()
        should_close = True

    try:
        db_orders = active_db.query(Order.product_id, Order.supplier_id).all()
        for pid, sid in db_orders:
            if sid and (str(sid).strip().upper() == target_sid or normalize_supplier_id(sid) == norm_target):
                authorized_products.add(str(pid).strip().upper())

        db_offers = active_db.query(SupplierOffer.product_id, SupplierOffer.supplier_id).all()
        for pid, sid in db_offers:
            if sid and (str(sid).strip().upper() == target_sid or normalize_supplier_id(sid) == norm_target):
                authorized_products.add(str(pid).strip().upper())
    except Exception:
        pass
    finally:
        if should_close:
            active_db.close()

    return authorized_products


def is_supplier_authorized(user_scope: QueryScope, target_supplier_id: str | None) -> bool:
    if user_scope.is_global:
        return True
    if not target_supplier_id:
        return True
    return supplier_ids_match(user_scope.supplier_id, target_supplier_id)


def is_product_authorized(
    user_scope: QueryScope,
    target_product_id: str | None,
    datasets: dict[str, pd.DataFrame] | None = None,
    db: Session | None = None,
) -> bool:
    if user_scope.is_global:
        return True
    if not target_product_id:
        return True
    authorized_products = get_supplier_authorized_products(
        user_scope.supplier_id or "", datasets, db
    )
    return str(target_product_id).strip().upper() in authorized_products


def validate_query_authorization(
    user_scope: QueryScope,
    plan: Any,
    datasets: dict[str, pd.DataFrame] | None = None,
    db: Session | None = None,
) -> tuple[bool, str, str]:
    """
    Validates whether the given QueryPlan is authorized for the user scope.
    Returns: (is_authorized, denial_reason, target_entity_desc)
    """
    if user_scope.is_global:
        return True, "", ""

    # SUPPLIER scope validation
    user_sid = user_scope.supplier_id or ""

    # Check top-level entity
    top_entity = getattr(plan, "entity", None)
    top_entity_id = getattr(plan, "entity_id", None)
    domain = getattr(plan, "domain", None)

    # Detect supplier entity in top-level plan
    if top_entity == "supplier" or (top_entity_id and str(top_entity_id).upper().startswith("S")):
        if top_entity_id and not supplier_ids_match(user_sid, top_entity_id):
            return False, f"Supplier {top_entity_id} is outside authorized scope", f"supplier {top_entity_id}"

    # Detect product entity in top-level plan
    if top_entity == "product" or (top_entity_id and str(top_entity_id).upper().startswith("P")):
        if top_entity_id and not is_product_authorized(user_scope, top_entity_id, datasets, db):
            return False, f"Product {top_entity_id} is not supplied by your organization", f"product {top_entity_id}"

    # Also check if original query mentions an explicit supplier entity that differs
    original_query = getattr(plan, "original_query", "")
    all_sids = re.findall(r"\b(S\d+)\b", original_query.upper())
    for sid in all_sids:
        if not supplier_ids_match(user_sid, sid):
            return False, f"Supplier {sid} is outside authorized scope", f"supplier {sid}"

    # Also check requirements
    requirements = getattr(plan, "requirements", []) or []
    for req in requirements:
        req_entity = getattr(req, "entity", None) if hasattr(req, "entity") else req.get("entity")
        req_entity_id = getattr(req, "entity_id", None) if hasattr(req, "entity_id") else req.get("entity_id")
        req_filters = getattr(req, "filters", {}) if hasattr(req, "filters") else req.get("filters", {})

        if req_entity == "supplier" or (req_entity_id and str(req_entity_id).upper().startswith("S")):
            if req_entity_id and not supplier_ids_match(user_sid, req_entity_id):
                return False, f"Supplier {req_entity_id} is outside authorized scope", f"supplier {req_entity_id}"

        if req_entity == "product" or (req_entity_id and str(req_entity_id).upper().startswith("P")):
            if req_entity_id and not is_product_authorized(user_scope, req_entity_id, datasets, db):
                return False, f"Product {req_entity_id} is not supplied by your organization", f"product {req_entity_id}"

        if req_filters:
            sids = req_filters.get("supplier_ids") or []
            if isinstance(sids, str):
                sids = [sids]
            for s in sids:
                if s and not supplier_ids_match(user_sid, s):
                    return False, f"Supplier {s} is outside authorized scope", f"supplier {s}"

            target_sid = req_filters.get("supplier_id")
            if target_sid and not supplier_ids_match(user_sid, target_sid):
                return False, f"Supplier {target_sid} is outside authorized scope", f"supplier {target_sid}"

    return True, "", ""
