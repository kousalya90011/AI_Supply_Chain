from __future__ import annotations

import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import get_raw_data_path
from app.models.database import get_db
from app.models.entities import Product, Supplier, SupplierOffer, User, UserRole, Order
from app.services.audit_service import AuditService
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/products", tags=["Products"])
audit_service = AuditService()


def generate_product_id(db: Session) -> str:
    """
    Auto-generates the next sequential unique Product ID (e.g. P02001, P02002).
    Takes into account both existing database products and the baseline catalog.
    """
    existing_ids = {row[0] for row in db.query(Product.product_id).all()}

    # Check if raw product_attributes.csv exists to prevent overlap with standard catalog
    try:
        raw_path = get_raw_data_path() / "product_attributes.csv"
        max_num = 2000 if raw_path.exists() else 0
    except Exception:
        max_num = 0

    for pid in existing_ids:
        match = re.match(r"^P(\d+)$", pid, re.IGNORECASE)
        if match:
            try:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num
            except ValueError:
                pass

    candidate_num = max_num + 1
    while True:
        candidate_id = f"P{candidate_num:05d}"
        if candidate_id not in existing_ids:
            return candidate_id
        candidate_num += 1


class ProductCreateRequest(BaseModel):
    product_id: str | None = None
    name: str = Field(..., min_length=2)
    category: str = Field(...)
    unit_cost: float = Field(..., ge=0)
    status: str = "ACTIVE"
    supplier_id: str | None = None


class ProductUpdateRequest(BaseModel):
    name: str | None = None
    category: str | None = None
    unit_cost: float | None = Field(default=None, ge=0)
    status: str | None = None


class ProductApprovalDecisionRequest(BaseModel):
    reason: str | None = None


class ProductResponse(BaseModel):
    product_id: str
    name: str
    category: str
    unit_cost: float
    status: str
    supplier_id: str | None = None
    approval_status: str = "APPROVED"
    approved_by: str | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        orm_mode = True


@router.get("", response_model=list[ProductResponse])
def list_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status_filter: str | None = Query(default=None, alias="status"),
    approval_status: str | None = Query(default=None, alias="approval_status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    if current_user.role == UserRole.SUPPLIER:
        if not current_user.supplier_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Supplier access denied")
        product_ids = (
            db.query(SupplierOffer.product_id)
            .filter(SupplierOffer.supplier_id == current_user.supplier_id)
            .union(db.query(Order.product_id).filter(Order.supplier_id == current_user.supplier_id))
            .all()
        )
        ids = {pid for (pid,) in product_ids}
        query = db.query(Product).filter(
            (Product.supplier_id == current_user.supplier_id) | (Product.product_id.in_(ids))
        )
        if status_filter:
            query = query.filter(Product.status == status_filter)
        if approval_status:
            query = query.filter(Product.approval_status == approval_status)
        return query.order_by(Product.created_at.desc()).offset(skip).limit(limit).all()

    if current_user.role not in {UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

    query = db.query(Product)
    if status_filter:
        query = query.filter(Product.status == status_filter)
    if approval_status:
        query = query.filter(Product.approval_status == approval_status)
    return query.order_by(Product.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/next-id")
def get_next_product_id(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Returns the next auto-generated Product ID.
    """
    return {"next_product_id": generate_product_id(db)}


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    if current_user.role == UserRole.SUPPLIER:
        if product.supplier_id != current_user.supplier_id:
            supplier_ids = (
                db.query(SupplierOffer.supplier_id)
                .filter(SupplierOffer.product_id == product_id, SupplierOffer.supplier_id == current_user.supplier_id)
                .union(db.query(Order.supplier_id).filter(Order.product_id == product_id, Order.supplier_id == current_user.supplier_id))
                .all()
            )
            if not supplier_ids:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Supplier access denied")
    elif current_user.role not in {UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

    return product


@router.post("", response_model=ProductResponse)
def create_product(payload: ProductCreateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in {UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER, UserRole.SUPPLIER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    product_id = payload.product_id.strip() if payload.product_id and payload.product_id.strip() else generate_product_id(db)

    if db.query(Product).filter(Product.product_id == product_id).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Product '{product_id}' already exists")

    if current_user.role == UserRole.SUPPLIER:
        if not current_user.supplier_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Supplier user is not linked to a supplier")
        product = Product(
            product_id=product_id,
            name=payload.name,
            category=payload.category,
            unit_cost=payload.unit_cost,
            status=payload.status or "ACTIVE",
            supplier_id=current_user.supplier_id,
            approval_status="PENDING",
        )
        db.add(product)
        db.flush()

        audit_service.record(
            query="PRODUCT_SUBMITTED",
            agent_name=current_user.username,
            input_data={
                "product_id": product.product_id,
                "name": product.name,
                "category": product.category,
                "unit_cost": product.unit_cost,
                "supplier_id": product.supplier_id,
            },
            output_data={"product_id": product.product_id, "approval_status": "PENDING"},
            db=db,
        )

        db.commit()
        db.refresh(product)
        return product

    # For ADMIN / SUPPLY_CHAIN_MANAGER
    product = Product(
        product_id=product_id,
        name=payload.name,
        category=payload.category,
        unit_cost=payload.unit_cost,
        status=payload.status or "ACTIVE",
        supplier_id=payload.supplier_id,
        approval_status="APPROVED",
        approved_by=current_user.username,
        approved_at=datetime.utcnow(),
    )
    db.add(product)
    db.flush()

    audit_service.record(
        query="PRODUCT_CREATED",
        agent_name=current_user.username,
        input_data={
            "product_id": product.product_id,
            "name": product.name,
            "category": product.category,
            "unit_cost": product.unit_cost,
            "supplier_id": product.supplier_id,
        },
        output_data={"product_id": product.product_id, "approval_status": "APPROVED"},
        db=db,
    )

    db.commit()
    db.refresh(product)
    return product


@router.patch("/{product_id}/approve", response_model=ProductResponse)
def approve_product(product_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in {UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only supply chain managers and admins can approve products")

    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    now = datetime.utcnow()
    product.approval_status = "APPROVED"
    product.approved_by = current_user.username
    product.approved_at = now
    product.rejection_reason = None
    product.updated_at = now

    audit_service.record(
        query="PRODUCT_APPROVED",
        agent_name=current_user.username,
        input_data={"product_id": product.product_id, "supplier_id": product.supplier_id},
        output_data={"product_id": product.product_id, "approval_status": "APPROVED", "approved_by": current_user.username},
        db=db,
    )

    db.commit()
    db.refresh(product)
    return product


@router.patch("/{product_id}/reject", response_model=ProductResponse)
def reject_product(
    product_id: str,
    payload: ProductApprovalDecisionRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only supply chain managers and admins can reject products")

    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    now = datetime.utcnow()
    product.approval_status = "REJECTED"
    product.approved_by = current_user.username
    product.approved_at = now
    product.rejection_reason = payload.reason if payload and payload.reason else "Product rejected by reviewer."
    product.updated_at = now

    audit_service.record(
        query="PRODUCT_REJECTED",
        agent_name=current_user.username,
        input_data={"product_id": product.product_id, "supplier_id": product.supplier_id, "reason": product.rejection_reason},
        output_data={"product_id": product.product_id, "approval_status": "REJECTED", "approved_by": current_user.username},
        db=db,
    )

    db.commit()
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: str, payload: ProductUpdateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in {UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or manager access required")
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    for field, value in payload.dict(exclude_unset=True).items():
        if value is not None:
            setattr(product, field, value)
    product.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}")
def delete_product(product_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"message": "Product deleted"}
