from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.entities import Inventory, Product, User, UserRole
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/inventory", tags=["Inventory"])


class InventoryCreateRequest(BaseModel):
    product_id: str = Field(...)
    date: datetime
    inventory_level: int = Field(..., ge=0)
    demand: int = Field(..., ge=0)
    stockout: bool = False


class InventoryUpdateRequest(BaseModel):
    product_id: str | None = None
    date: datetime | None = None
    inventory_level: int | None = Field(default=None, ge=0)
    demand: int | None = Field(default=None, ge=0)
    stockout: bool | None = None


class InventoryResponse(BaseModel):
    id: int
    product_id: str
    date: datetime
    inventory_level: int
    demand: int
    stockout: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        orm_mode = True


@router.get("", response_model=list[InventoryResponse])
def list_inventory(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    if current_user.role == UserRole.SUPPLIER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Suppliers cannot manage inventory")
    if current_user.role not in {UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")
    return db.query(Inventory).offset(skip).limit(limit).all()


@router.get("/{inventory_id}", response_model=InventoryResponse)
def get_inventory(inventory_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == UserRole.SUPPLIER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Suppliers cannot manage inventory")
    if current_user.role not in {UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")
    inventory = db.query(Inventory).filter(Inventory.id == inventory_id).first()
    if not inventory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory record not found")
    return inventory


@router.post("", response_model=InventoryResponse)
def create_inventory(payload: InventoryCreateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in {UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or manager access required")
    if not db.query(Product).filter(Product.product_id == payload.product_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    inventory = Inventory(
        product_id=payload.product_id,
        date=payload.date,
        inventory_level=payload.inventory_level,
        demand=payload.demand,
        stockout=payload.stockout,
    )
    db.add(inventory)
    db.commit()
    db.refresh(inventory)
    return inventory


@router.put("/{inventory_id}", response_model=InventoryResponse)
def update_inventory(inventory_id: int, payload: InventoryUpdateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in {UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or manager access required")
    inventory = db.query(Inventory).filter(Inventory.id == inventory_id).first()
    if not inventory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory record not found")
    for field, value in payload.dict(exclude_unset=True).items():
        if value is not None:
            setattr(inventory, field, value)
    inventory.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(inventory)
    return inventory


@router.delete("/{inventory_id}")
def delete_inventory(inventory_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    inventory = db.query(Inventory).filter(Inventory.id == inventory_id).first()
    if not inventory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory record not found")
    db.delete(inventory)
    db.commit()
    return {"message": "Inventory record deleted"}
