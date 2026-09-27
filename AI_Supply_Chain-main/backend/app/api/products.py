from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.entities import Product, Supplier, SupplierOffer, User, UserRole, Order
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/products", tags=["Products"])


class ProductCreateRequest(BaseModel):
    product_id: str = Field(..., min_length=2)
    name: str = Field(..., min_length=2)
    category: str = Field(...)
    unit_cost: float = Field(..., ge=0)
    status: str = "ACTIVE"


class ProductUpdateRequest(BaseModel):
    name: str | None = None
    category: str | None = None
    unit_cost: float | None = Field(default=None, ge=0)
    status: str | None = None


class ProductResponse(BaseModel):
    product_id: str
    name: str
    category: str
    unit_cost: float
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        orm_mode = True


@router.get("", response_model=list[ProductResponse])
def list_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
        return db.query(Product).filter(Product.product_id.in_(ids)).offset(skip).limit(limit).all()

    if current_user.role not in {UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

    return db.query(Product).offset(skip).limit(limit).all()


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    if current_user.role == UserRole.SUPPLIER:
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
    if current_user.role not in {UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or manager access required")
    if db.query(Product).filter(Product.product_id == payload.product_id).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product already exists")
    product = Product(
        product_id=payload.product_id,
        name=payload.name,
        category=payload.category,
        unit_cost=payload.unit_cost,
        status=payload.status,
    )
    db.add(product)
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
