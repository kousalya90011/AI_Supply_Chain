from fastapi.testclient import TestClient

from app.main import app
from app.models.database import SessionLocal
from app.models.entities import User, UserRole
from app.services.auth_service import get_password_hash


def _reset_users():
    db = SessionLocal()
    try:
        db.query(User).delete()
        db.commit()
    finally:
        db.close()

client = TestClient(app)


def _create_supplier_user(username: str, password: str, supplier_id: str):
    db = SessionLocal()
    try:
        user = User(
            username=username,
            email=f"{username}@example.com",
            password_hash=get_password_hash(password),
            role=UserRole.SUPPLIER.value,
            supplier_id=supplier_id,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def test_admin_login_and_me():
    _reset_users()
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert "access_token" in body

    token = body["access_token"]
    me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me.status_code == 200, me.text
    assert me.json()["role"] == UserRole.ADMIN.value


def test_supplier_role_is_restricted_to_own_supplier():
    _reset_users()
    _create_supplier_user("supplier_alpha", "pw123", "S001")

    login = client.post(
        "/api/auth/login",
        json={"username": "supplier_alpha", "password": "pw123"},
    )
    assert login.status_code == 200, login.text

    token = login.json()["access_token"]
    allowed = client.get(
        "/api/auth/verify-supplier-access/S001",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["authorized"] is True

    blocked = client.get(
        "/api/auth/verify-supplier-access/S002",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert blocked.status_code == 403, blocked.text
