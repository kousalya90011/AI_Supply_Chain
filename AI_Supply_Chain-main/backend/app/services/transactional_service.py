from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.entities import (
    AuditTrace,
    Inventory,
    Order,
    Product,
    Supplier,
    SupplierOffer,
    User,
    UserRole,
)


class TransactionalService:
    @staticmethod
    def require_admin(current_user: User) -> None:
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )

    @staticmethod
    def require_admin_or_manager(current_user: User) -> None:
        if current_user.role not in {UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin or manager access required",
            )

    @staticmethod
    def require_supplier_scope(current_user: User, supplier_id: str | None) -> None:
        if current_user.role == UserRole.ADMIN or current_user.role == UserRole.SUPPLY_CHAIN_MANAGER:
            return
        if current_user.role == UserRole.SUPPLIER:
            if supplier_id is None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Supplier access denied")
            if current_user.supplier_id and current_user.supplier_id == supplier_id:
                return
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Supplier access denied")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

    @staticmethod
    def enforce_supplier_row_filter(db: Session, current_user: User, model: type[Any], supplier_field: str = "supplier_id") -> Any:
        if current_user.role in {UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER}:
            return db.query(model)

        if current_user.role == UserRole.SUPPLIER:
            if current_user.supplier_id is None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Supplier access denied")

            if model is Supplier:
                return db.query(model).filter(getattr(model, supplier_field) == current_user.supplier_id)

            if model is SupplierOffer:
                return db.query(model).filter(getattr(model, supplier_field) == current_user.supplier_id)

            if model is Order:
                return db.query(model).filter(getattr(model, supplier_field) == current_user.supplier_id)

            if model is Product:
                product_ids = (
                    db.query(SupplierOffer.product_id)
                    .filter(SupplierOffer.supplier_id == current_user.supplier_id)
                    .union(
                        db.query(Order.product_id).filter(Order.supplier_id == current_user.supplier_id)
                    )
                    .subquery()
                )
                return db.query(model).filter(model.product_id.in_(db.query(product_ids.c.product_id)))

            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Supplier access denied")

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

    @staticmethod
    def ensure_supplier_exists(db: Session, supplier_id: str) -> Supplier:
        supplier = db.query(Supplier).filter(Supplier.supplier_id == supplier_id).first()
        if not supplier:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
        return supplier

    @staticmethod
    def ensure_product_exists(db: Session, product_id: str) -> Product:
        product = db.query(Product).filter(Product.product_id == product_id).first()
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        return product

    @staticmethod
    def ensure_order_exists(db: Session, order_id: int) -> Order:
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        return order

    @staticmethod
    def ensure_offer_exists(db: Session, offer_id: int) -> SupplierOffer:
        offer = db.query(SupplierOffer).filter(SupplierOffer.offer_id == offer_id).first()
        if not offer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")
        return offer

    @staticmethod
    def ensure_offer_is_pending(offer: SupplierOffer) -> None:
        if offer.status != "PENDING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Offer must be PENDING, current status is {offer.status}",
            )

    @staticmethod
    def create_audit(db: Session, query: str, agent_name: str, input_data: Any, output_data: Any) -> AuditTrace:
        trace = AuditTrace(
            query=query,
            agent_name=agent_name,
            input_data=str(input_data),
            output_data=str(output_data),
        )
        db.add(trace)
        return trace

    @staticmethod
    def order_from_offer(offer: SupplierOffer, status: str = "PENDING") -> Order:
        return Order(
            product_id=offer.product_id,
            supplier_id=offer.supplier_id,
            quantity=offer.quantity,
            unit_price=offer.unit_price,
            order_date=datetime.utcnow(),
            requested_delivery_date=datetime.utcnow(),
            expected_delivery_date=datetime.utcnow(),
            actual_delivery_date=None,
            status=status,
        )
