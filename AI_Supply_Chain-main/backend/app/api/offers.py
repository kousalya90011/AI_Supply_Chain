from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.entities import Order, Product, Supplier, SupplierOffer, User, UserRole
from app.services.audit_service import AuditService
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/offers", tags=["Offers"])
audit_service = AuditService()


class SupplierOfferCreateRequest(BaseModel):
    supplier_id: str | None = None
    product_id: str = Field(...)
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    delivery_days: int = Field(..., ge=1)
    valid_until: datetime


class SupplierOfferUpdateRequest(BaseModel):
    quantity: int | None = Field(default=None, gt=0)
    unit_price: float | None = Field(default=None, ge=0)
    delivery_days: int | None = Field(default=None, ge=1)
    valid_until: datetime | None = None


class SupplierOfferResponse(BaseModel):
    offer_id: int
    supplier_id: str
    product_id: str
    quantity: int
    unit_price: float
    delivery_days: int
    valid_until: datetime
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None

    class Config:
        orm_mode = True


class OfferDecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(ACCEPTED|REJECTED)$")


@router.get("", response_model=list[SupplierOfferResponse])
def list_offers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status_filter: str | None = Query(default=None, alias="status"),
    supplier_id: str | None = None,
    supplier: str | None = None,
    product_id: str | None = None,
    product: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    target_supplier = supplier_id or supplier
    target_product = product_id or product

    if current_user.role == UserRole.SUPPLIER:
        if not current_user.supplier_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Supplier access denied")
        if target_supplier and target_supplier != current_user.supplier_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Supplier access denied")

        query = db.query(SupplierOffer).filter(SupplierOffer.supplier_id == current_user.supplier_id)
        if status_filter:
            query = query.filter(SupplierOffer.status == status_filter)
        if target_product:
            query = query.filter(SupplierOffer.product_id == target_product)
        return query.order_by(SupplierOffer.offer_id.desc()).offset(skip).limit(limit).all()

    if current_user.role not in {UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

    query = db.query(SupplierOffer)
    if target_supplier:
        query = query.filter(SupplierOffer.supplier_id == target_supplier)
    if status_filter:
        query = query.filter(SupplierOffer.status == status_filter)
    if target_product:
        query = query.filter(SupplierOffer.product_id == target_product)
    return query.order_by(SupplierOffer.offer_id.desc()).offset(skip).limit(limit).all()


@router.get("/{offer_id}", response_model=SupplierOfferResponse)
def get_offer(offer_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    offer = db.query(SupplierOffer).filter(SupplierOffer.offer_id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")

    if current_user.role == UserRole.SUPPLIER:
        if current_user.supplier_id != offer.supplier_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Supplier access denied")
    elif current_user.role not in {UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

    return offer


@router.post("", response_model=SupplierOfferResponse)
def create_offer(
    payload: SupplierOfferCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.SUPPLIER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only suppliers can create offers")

    if not current_user.supplier_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Supplier user is not linked to a supplier")

    # Backend MUST derive supplier_id from the authenticated supplier user.
    # Never trust supplier_id from the frontend request.
    supplier_id = current_user.supplier_id

    if not db.query(Supplier).filter(Supplier.supplier_id == supplier_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    if not db.query(Product).filter(Product.product_id == payload.product_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    try:
        offer = SupplierOffer(
            supplier_id=supplier_id,
            product_id=payload.product_id,
            quantity=payload.quantity,
            unit_price=payload.unit_price,
            delivery_days=payload.delivery_days,
            valid_until=payload.valid_until,
            status="PENDING",
        )
        db.add(offer)
        db.flush()

        audit_service.record(
            query="OFFER_CREATED",
            agent_name=current_user.username,
            input_data={
                "product_id": offer.product_id,
                "quantity": offer.quantity,
                "unit_price": offer.unit_price,
                "delivery_days": offer.delivery_days,
                "valid_until": str(offer.valid_until),
            },
            output_data={
                "offer_id": offer.offer_id,
                "supplier_id": offer.supplier_id,
                "status": offer.status,
            },
            db=db,
        )

        db.commit()
        db.refresh(offer)
        return offer
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.put("/{offer_id}", response_model=SupplierOfferResponse)
def update_offer(
    offer_id: int,
    payload: SupplierOfferUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    offer = db.query(SupplierOffer).filter(SupplierOffer.offer_id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")

    if current_user.role == UserRole.SUPPLIER:
        if current_user.supplier_id != offer.supplier_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Supplier access denied")
        if offer.status != "PENDING":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PENDING offers can be edited")
    elif current_user.role not in {UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

    if offer.status != "PENDING":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PENDING offers can be edited")

    try:
        update_data = payload.dict(exclude_unset=True) if hasattr(payload, "dict") else payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(offer, field, value)
        offer.updated_at = datetime.utcnow()

        audit_service.record(
            query="OFFER_UPDATED",
            agent_name=current_user.username,
            input_data={"offer_id": offer_id, "changes": update_data},
            output_data={"offer_id": offer_id, "status": offer.status},
            db=db,
        )

        db.commit()
        db.refresh(offer)
        return offer
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.patch("/{offer_id}/accept")
def accept_offer(
    offer_id: int,
    payload: dict | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in {UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin or manager can accept offers")

    offer = db.query(SupplierOffer).filter(SupplierOffer.offer_id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")
    if offer.status != "PENDING":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Offer is not pending")

    try:
        now = datetime.utcnow()
        offer.status = "ACCEPTED"
        offer.reviewed_at = now
        offer.reviewed_by = current_user.username
        offer.updated_at = now

        delivery_days = offer.delivery_days or 7
        expected_delivery = now + timedelta(days=delivery_days)

        order = Order(
            supplier_id=offer.supplier_id,
            product_id=offer.product_id,
            quantity=offer.quantity,
            unit_price=offer.unit_price,
            order_date=now,
            requested_delivery_date=expected_delivery,
            expected_delivery_date=expected_delivery,
            actual_delivery_date=None,
            status="PENDING",
        )
        db.add(order)
        db.flush()

        audit_service.record(
            query="OFFER_ACCEPTED",
            agent_name=current_user.username,
            input_data={"offer_id": offer.offer_id, "supplier_id": offer.supplier_id},
            output_data={"status": "ACCEPTED", "event": "offer accepted", "order_id": order.order_id},
            db=db,
        )
        audit_service.record(
            query="ORDER_CREATED",
            agent_name=current_user.username,
            input_data={
                "offer_id": offer.offer_id,
                "supplier_id": offer.supplier_id,
                "product_id": offer.product_id,
                "quantity": offer.quantity,
                "unit_price": offer.unit_price,
            },
            output_data={"order_id": order.order_id, "status": order.status},
            db=db,
        )

        db.commit()
        db.refresh(offer)
        db.refresh(order)
        return {
            "offer": {
                "offer_id": offer.offer_id,
                "supplier_id": offer.supplier_id,
                "product_id": offer.product_id,
                "quantity": offer.quantity,
                "unit_price": offer.unit_price,
                "delivery_days": offer.delivery_days,
                "valid_until": offer.valid_until.isoformat() if offer.valid_until else None,
                "status": offer.status,
                "created_at": offer.created_at.isoformat() if offer.created_at else None,
                "updated_at": offer.updated_at.isoformat() if offer.updated_at else None,
                "reviewed_at": offer.reviewed_at.isoformat() if offer.reviewed_at else None,
                "reviewed_by": offer.reviewed_by,
            },
            "order": {
                "order_id": order.order_id,
                "supplier_id": order.supplier_id,
                "product_id": order.product_id,
                "quantity": order.quantity,
                "unit_price": order.unit_price,
                "order_date": order.order_date.isoformat() if order.order_date else None,
                "requested_delivery_date": order.requested_delivery_date.isoformat() if order.requested_delivery_date else None,
                "expected_delivery_date": order.expected_delivery_date.isoformat() if order.expected_delivery_date else None,
                "actual_delivery_date": order.actual_delivery_date.isoformat() if order.actual_delivery_date else None,
                "status": order.status,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "updated_at": order.updated_at.isoformat() if order.updated_at else None,
            },
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.patch("/{offer_id}/reject", response_model=SupplierOfferResponse)
def reject_offer(
    offer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in {UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin or manager can reject offers")

    offer = db.query(SupplierOffer).filter(SupplierOffer.offer_id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")
    if offer.status != "PENDING":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Offer is not pending")

    try:
        now = datetime.utcnow()
        offer.status = "REJECTED"
        offer.reviewed_at = now
        offer.reviewed_by = current_user.username
        offer.updated_at = now

        audit_service.record(
            query="OFFER_REJECTED",
            agent_name=current_user.username,
            input_data={"offer_id": offer.offer_id, "supplier_id": offer.supplier_id},
            output_data={"status": "REJECTED"},
            db=db,
        )

        db.commit()
        db.refresh(offer)
        return offer
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.patch("/{offer_id}/withdraw", response_model=SupplierOfferResponse)
def withdraw_offer(
    offer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.SUPPLIER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only suppliers can withdraw offers")

    offer = db.query(SupplierOffer).filter(SupplierOffer.offer_id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")
    if current_user.supplier_id != offer.supplier_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Supplier access denied")
    if offer.status != "PENDING":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PENDING offers can be withdrawn")

    try:
        offer.status = "WITHDRAWN"
        offer.updated_at = datetime.utcnow()

        audit_service.record(
            query="OFFER_WITHDRAWN",
            agent_name=current_user.username,
            input_data={"offer_id": offer.offer_id, "supplier_id": offer.supplier_id},
            output_data={"status": "WITHDRAWN"},
            db=db,
        )

        db.commit()
        db.refresh(offer)
        return offer
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.delete("/{offer_id}")
def delete_offer(
    offer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in {UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or manager access required")
    offer = db.query(SupplierOffer).filter(SupplierOffer.offer_id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")
    db.delete(offer)
    db.commit()
    return {"message": "Offer deleted"}
