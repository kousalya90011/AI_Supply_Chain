from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.entities import User, UserRole, Supplier
from app.services.auth_service import get_current_user, get_password_hash


router = APIRouter(prefix="/api/users", tags=["Users"])


# =========================================================
# REQUEST / RESPONSE MODELS
# =========================================================

class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3)
    email: str
    password: str = Field(..., min_length=6)
    name: str
    role: str = UserRole.SUPPLIER
    # Supplier ID is intentionally NOT required from frontend.
    # Backend generates it automatically for SUPPLIER users.
    supplier_id: str | None = None
    status: str = "ACTIVE"


class UserUpdateRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    role: str | None = None
    supplier_id: str | None = None
    status: str | None = None


class UserResponse(BaseModel):
    id: int
    username: str
    name: str | None = None
    email: str
    role: str
    supplier_id: str | None = None
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        orm_mode = True


# =========================================================
# SUPPLIER ID GENERATOR
# =========================================================

def generate_supplier_id(db: Session) -> str:
    """
    Generate the next supplier ID.

    Examples:
        S001
        S002
        S003
        ...
    """

    suppliers = (
        db.query(Supplier.supplier_id)
        .filter(Supplier.supplier_id.like("S%"))
        .all()
    )

    max_number = 0

    for row in suppliers:
        supplier_id = row[0]

        if not supplier_id:
            continue

        try:
            number = int(supplier_id[1:])
            max_number = max(max_number, number)
        except (ValueError, TypeError):
            continue

    return f"S{max_number + 1:03d}"


# =========================================================
# LIST USERS
# =========================================================

@router.get("", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    users = (
        db.query(User)
        .offset(skip)
        .limit(limit)
        .all()
    )

    return users


# =========================================================
# GET USER
# =========================================================

@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


# =========================================================
# CREATE USER
# =========================================================

@router.post("", response_model=UserResponse)
def create_user(
    payload: UserCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    # -----------------------------------------------------
    # Username uniqueness
    # -----------------------------------------------------

    if db.query(User).filter(
        User.username == payload.username
    ).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    # -----------------------------------------------------
    # Email uniqueness
    # -----------------------------------------------------

    if db.query(User).filter(
        User.email == payload.email
    ).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists",
        )

    # -----------------------------------------------------
    # Validate role
    # -----------------------------------------------------

    valid_roles = {
        UserRole.ADMIN,
        UserRole.SUPPLY_CHAIN_MANAGER,
        UserRole.SUPPLIER,
    }

    if payload.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role",
        )

    # -----------------------------------------------------
    # AUTO GENERATE SUPPLIER ID
    # -----------------------------------------------------

    supplier_id = None

    if payload.role == UserRole.SUPPLIER:

        supplier_id = generate_supplier_id(db)

        # Create the corresponding supplier record as well.
        #
        # This is important because your Offers API checks:
        #
        #     Supplier.supplier_id
        #
        # before allowing a supplier to create an offer.

        supplier = Supplier(
            supplier_id=supplier_id,
            name=payload.name,
            region="UNKNOWN",
            tier="STANDARD",
            status="ACTIVE",
        )

        db.add(supplier)

    # -----------------------------------------------------
    # Create user
    # -----------------------------------------------------

    user = User(
        username=payload.username,
        name=payload.name,
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        role=payload.role,
        supplier_id=supplier_id,
        status=payload.status,
    )

    db.add(user)

    try:
        db.commit()
        db.refresh(user)

        return user

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to create user: {str(exc)}",
        )


# =========================================================
# UPDATE USER
# =========================================================

@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    update_data = payload.model_dump(exclude_unset=True)

    # Supplier ID should not be manually changed for supplier users.
    if user.role == UserRole.SUPPLIER:
        update_data.pop("supplier_id", None)

    for field, value in update_data.items():
        if value is not None:
            setattr(user, field, value)

    user.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(user)

    return user


# =========================================================
# DELETE USER
# =========================================================

@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    db.delete(user)
    db.commit()

    return {"message": "User deleted"}
