from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.entities import User, UserRole
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    ensure_default_admin,
    get_current_user,
    get_password_hash,
    require_supplier_scope,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=3)


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str = UserRole.SUPPLIER
    supplier_id: str | None = None


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    ensure_default_admin(db)
    user = authenticate_user(db, payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(user.username, user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "username": user.username,
    }


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "supplier_id": current_user.supplier_id,
        "is_active": current_user.is_active,
    }


@router.get("/verify-supplier-access/{supplier_id}")
def verify_supplier_access(supplier_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role == UserRole.ADMIN or current_user.role == UserRole.SUPPLY_CHAIN_MANAGER:
        return {"authorized": True, "supplier_id": supplier_id, "role": current_user.role}

    if current_user.role == UserRole.SUPPLIER:
        if current_user.supplier_id and current_user.supplier_id == supplier_id:
            return {"authorized": True, "supplier_id": supplier_id, "role": current_user.role}
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Supplier access denied")

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")


@router.post("/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    if payload.role not in {UserRole.ADMIN, UserRole.SUPPLY_CHAIN_MANAGER, UserRole.SUPPLIER}:
        raise HTTPException(status_code=400, detail="Invalid role")

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        role=payload.role,
        supplier_id=payload.supplier_id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "User created", "user_id": user.id, "role": user.role}


@router.get("/admin-only")
def admin_only(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return {"message": "admin ok"}
