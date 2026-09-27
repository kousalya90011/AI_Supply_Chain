from datetime import datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.models.database import get_db
from app.models.entities import User, UserRole

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str, role: str) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": subject,
        "role": role,
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": now,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = get_user_by_username(db, username)
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def ensure_default_admin(db: Session) -> User:
    user = db.query(User).filter(User.username == settings.DEFAULT_ADMIN_USERNAME).first()
    desired_hash = get_password_hash(settings.DEFAULT_ADMIN_PASSWORD)
    if user is None:
        user = User(
            username=settings.DEFAULT_ADMIN_USERNAME,
            email="admin@supplychain.local",
            password_hash=desired_hash,
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(user)
    else:
        needs_update = (
            user.password_hash != desired_hash
            or user.role != UserRole.ADMIN
            or not user.is_active
        )
        if needs_update:
            user.password_hash = desired_hash
            user.role = UserRole.ADMIN
            user.is_active = True
            user.email = user.email or "admin@supplychain.local"
    db.commit()
    db.refresh(user)
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    payload = decode_token(token)
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def require_roles(*roles: str):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return dependency


def require_supplier_scope(supplier_id: str, current_user: User = Depends(get_current_user)) -> User:
    if current_user.role == UserRole.ADMIN or current_user.role == UserRole.SUPPLY_CHAIN_MANAGER:
        return current_user
    if current_user.role == UserRole.SUPPLIER:
        if current_user.supplier_id and current_user.supplier_id == supplier_id:
            return current_user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Supplier access denied")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")


security_optional = HTTPBearer(auto_error=False)


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_optional),
    db: Session = Depends(get_db),
) -> User | None:
    if not credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
        username = payload.get("sub")
        if not username:
            return None
        return db.query(User).filter(User.username == username, User.is_active == True).first()
    except Exception:
        return None

