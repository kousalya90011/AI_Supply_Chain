from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.entities import Supplier, User, UserRole
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/suppliers", tags=["Suppliers"])


class SupplierCreateRequest(BaseModel):
    supplier_id: str = Field(..., min_length=2, max_length=100)
    name: str = Field(..., min_length=2)
    region: str = Field(...)
    tier: str = Field(...)
    status: str = "ACTIVE"


class SupplierUpdateRequest(BaseModel):
    name: str | None = None
    region: str | None = None
    tier: str | None = None
    status: str | None = None


class SupplierResponse(BaseModel):
    supplier_id: str
    name: str
    region: str
    tier: str
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        orm_mode = True


@router.get("", response_model=list[SupplierResponse])
def list_suppliers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    if current_user.role == UserRole.SUPPLIER:
        if not current_user.supplier_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Supplier access denied")
        suppliers = db.query(Supplier).filter(Supplier.supplier_id == current_user.supplier_id).offset(skip).limit(limit).all()
        return suppliers
    if current_user.role not in {UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")
    return db.query(Supplier).offset(skip).limit(limit).all()


@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier(supplier_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    supplier = db.query(Supplier).filter(Supplier.supplier_id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    if current_user.role == UserRole.SUPPLIER:
        if current_user.supplier_id != supplier_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Supplier access denied")
    elif current_user.role not in {UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")
    return supplier


@router.post("", response_model=SupplierResponse)
def create_supplier(payload: SupplierCreateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in {UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or manager access required")
    if db.query(Supplier).filter(Supplier.supplier_id == payload.supplier_id).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Supplier already exists")
    supplier = Supplier(
        supplier_id=payload.supplier_id,
        name=payload.name,
        region=payload.region,
        tier=payload.tier,
        status=payload.status,
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.put("/{supplier_id}", response_model=SupplierResponse)
def update_supplier(supplier_id: str, payload: SupplierUpdateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in {UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or manager access required")
    supplier = db.query(Supplier).filter(Supplier.supplier_id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    for field, value in payload.dict(exclude_unset=True).items():
        if value is not None:
            setattr(supplier, field, value)
    supplier.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(supplier)
    return supplier


@router.delete("/{supplier_id}")
def delete_supplier(supplier_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    supplier = db.query(Supplier).filter(Supplier.supplier_id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    db.delete(supplier)
    db.commit()
    return {"message": "Supplier deleted"}
