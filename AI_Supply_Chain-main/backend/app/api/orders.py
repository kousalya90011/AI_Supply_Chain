from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.entities import Order, Product, Supplier, User, UserRole
from app.services.audit_service import AuditService
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/orders", tags=["Orders"])
audit_service = AuditService()


class OrderCreateRequest(BaseModel):
    product_id: str = Field(...)
    supplier_id: str = Field(...)
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    order_date: datetime | None = None
    requested_delivery_date: datetime | None = None
    expected_delivery_date: datetime | None = None
    actual_delivery_date: datetime | None = None
    status: str = "PENDING"


class OrderUpdateRequest(BaseModel):
    product_id: str | None = None
    supplier_id: str | None = None
    quantity: int | None = Field(default=None, gt=0)
    unit_price: float | None = Field(default=None, ge=0)
    order_date: datetime | None = None
    requested_delivery_date: datetime | None = None
    expected_delivery_date: datetime | None = None
    actual_delivery_date: datetime | None = None
    status: str | None = None


class OrderResponse(BaseModel):
    order_id: int
    product_id: str
    supplier_id: str
    quantity: int
    unit_price: float
    order_date: datetime | None = None
    requested_delivery_date: datetime | None = None
    expected_delivery_date: datetime | None = None
    actual_delivery_date: datetime | None = None
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        orm_mode = True


@router.get("", response_model=list[OrderResponse])
def list_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    supplier_id: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    if current_user.role == UserRole.SUPPLIER:
        if not current_user.supplier_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Supplier access denied")
        query = db.query(Order).filter(Order.supplier_id == current_user.supplier_id)
        if supplier_id and supplier_id != current_user.supplier_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Supplier access denied")
        return query.offset(skip).limit(limit).all()

    if current_user.role not in {UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

    query = db.query(Order)
    if supplier_id:
        query = query.filter(Order.supplier_id == supplier_id)
    return query.offset(skip).limit(limit).all()


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if current_user.role == UserRole.SUPPLIER:
        if current_user.supplier_id != order.supplier_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Supplier access denied")
    elif current_user.role not in {UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

    return order


@router.post("", response_model=OrderResponse)
def create_order(payload: OrderCreateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in {UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or manager access required")

    if not db.query(Product).filter(Product.product_id == payload.product_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if not db.query(Supplier).filter(Supplier.supplier_id == payload.supplier_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")

    order = Order(
        product_id=payload.product_id,
        supplier_id=payload.supplier_id,
        quantity=payload.quantity,
        unit_price=payload.unit_price,
        order_date=payload.order_date or datetime.utcnow(),
        requested_delivery_date=payload.requested_delivery_date or datetime.utcnow(),
        expected_delivery_date=payload.expected_delivery_date or datetime.utcnow(),
        actual_delivery_date=payload.actual_delivery_date,
        status=payload.status,
    )
    db.add(order)
    db.flush()

    audit_service.record(
        query="ORDER_CREATED",
        agent_name=current_user.username,
        input_data={"product_id": payload.product_id, "supplier_id": payload.supplier_id, "quantity": payload.quantity},
        output_data={"order_id": order.order_id, "status": order.status},
        db=db,
    )

    db.commit()
    db.refresh(order)
    return order


@router.put("/{order_id}", response_model=OrderResponse)
def update_order(order_id: int, payload: OrderUpdateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in {UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or manager access required")
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    for field, value in payload.dict(exclude_unset=True).items():
        if value is not None:
            setattr(order, field, value)
    order.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return order


@router.delete("/{order_id}")
def delete_order(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    db.delete(order)
    db.commit()
    return {"message": "Order deleted"}
