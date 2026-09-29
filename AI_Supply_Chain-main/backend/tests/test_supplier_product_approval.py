import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.models.database import Base, SessionLocal, engine
from app.models.entities import Product, Supplier, SupplierOffer, User, UserRole
from app.services.auth_service import get_password_hash, ensure_default_admin

client = TestClient(app)


def seed_standard_data():
    db = SessionLocal()
    try:
        ensure_default_admin(db)
        for sid, sname in [('S001', 'Supplier Alpha'), ('S002', 'Supplier Beta'), ('S0147', 'Global Logistics')]:
            if not db.query(Supplier).filter(Supplier.supplier_id == sid).first():
                db.add(Supplier(supplier_id=sid, name=sname, region='Global', tier='TIER_1', status='ACTIVE'))
        users = [
            ('admin_user', 'admin@scm.test', 'AdminPass123!', UserRole.ADMIN, None, 'Admin User'),
            ('supplier_user1', 'sup1@scm.test', 'SupplierPass123!', UserRole.SUPPLIER, 'S001', 'Supplier 1'),
            ('supplier_user2', 'sup2@scm.test', 'SupplierPass123!', UserRole.SUPPLIER, 'S002', 'Supplier 2'),
            ('chunking chain', 'manager@scm.test', 'ManagerPass123!', UserRole.SUPPLY_CHAIN_MANAGER, None, 'Manager User'),
        ]
        for u, em, pw, r, sup, nm in users:
            if not db.query(User).filter(User.username == u).first():
                db.add(User(username=u, email=em, password_hash=get_password_hash(pw), role=r, supplier_id=sup, name=nm, status='ACTIVE', is_active=True))
        prods = [
            ('P00001', 'Alpha Component', 'Electronics', 50.0, 'ACTIVE', 'APPROVED'),
            ('P00002', 'Beta Widget', 'Electronics', 100.0, 'ACTIVE', 'APPROVED'),
            ('P00003', 'Consumer Gadget', 'Consumer', 53.38, 'ACTIVE', 'APPROVED'),
        ]
        for pid, nm, cat, cost, st, app_st in prods:
            if not db.query(Product).filter(Product.product_id == pid).first():
                db.add(Product(product_id=pid, name=nm, category=cat, unit_cost=cost, status=st, approval_status=app_st))
        db.commit()
    finally:
        db.close()


def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def create_user(username, email, password, role, supplier_id=None, name=None):
    db = SessionLocal()
    try:
        user = User(
            username=username,
            email=email,
            password_hash=get_password_hash(password),
            role=role,
            supplier_id=supplier_id,
            name=name or username,
            status="ACTIVE",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def login(username, password):
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def make_supplier(supplier_id, name):
    db = SessionLocal()
    try:
        s = Supplier(supplier_id=supplier_id, name=name, region="Global", tier="TIER_1", status="ACTIVE")
        db.add(s)
        db.commit()
        db.refresh(s)
        return s
    finally:
        db.close()


def test_supplier_product_submission_and_approval_flow():
    reset_db()

    # 1. Setup users: Admin, Manager, Supplier
    make_supplier("S100", "Acme Supplier")
    create_user("admin_user", "admin@test.com", "pass123", UserRole.ADMIN, name="Admin")
    create_user("manager_user", "mgr@test.com", "pass123", UserRole.SUPPLY_CHAIN_MANAGER, name="Manager")
    create_user("supplier_acme", "acme@test.com", "pass123", UserRole.SUPPLIER, supplier_id="S100", name="Acme")

    admin_token = login("admin_user", "pass123")
    manager_token = login("manager_user", "pass123")
    supplier_token = login("supplier_acme", "pass123")

    # 2. Supplier adds a product
    create_prod_resp = client.post(
        "/api/products",
        headers={"Authorization": f"Bearer {supplier_token}"},
        json={
            "product_id": "PRD-NEW-1",
            "name": "Acme Solar Cell",
            "category": "Photovoltaics",
            "unit_cost": 85.0,
            "status": "ACTIVE",
        },
    )
    assert create_prod_resp.status_code == 200, create_prod_resp.text
    prod_data = create_prod_resp.json()
    assert prod_data["product_id"] == "PRD-NEW-1"
    assert prod_data["supplier_id"] == "S100"
    assert prod_data["approval_status"] == "PENDING"

    # 3. Supplier CANNOT create offer while product is PENDING
    offer_attempt = client.post(
        "/api/offers",
        headers={"Authorization": f"Bearer {supplier_token}"},
        json={
            "product_id": "PRD-NEW-1",
            "quantity": 50,
            "unit_price": 90.0,
            "delivery_days": 5,
            "valid_until": "2030-01-01T00:00:00",
        },
    )
    assert offer_attempt.status_code == 400
    assert "not approved" in offer_attempt.json()["detail"].lower()

    # 4. Supplier cannot approve their own product
    sup_approve = client.patch(
        "/api/products/PRD-NEW-1/approve",
        headers={"Authorization": f"Bearer {supplier_token}"},
    )
    assert sup_approve.status_code == 403

    # 5. Supply chain MANAGER approves the product
    mgr_approve = client.patch(
        "/api/products/PRD-NEW-1/approve",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert mgr_approve.status_code == 200, mgr_approve.text
    approved_data = mgr_approve.json()
    assert approved_data["approval_status"] == "APPROVED"
    assert approved_data["approved_by"] == "manager_user"

    # 6. NOW supplier CAN create offer on the approved product!
    offer_success = client.post(
        "/api/offers",
        headers={"Authorization": f"Bearer {supplier_token}"},
        json={
            "product_id": "PRD-NEW-1",
            "quantity": 50,
            "unit_price": 90.0,
            "delivery_days": 5,
            "valid_until": "2030-01-01T00:00:00",
        },
    )
    assert offer_success.status_code == 200, offer_success.text
    assert offer_success.json()["status"] == "PENDING"
    assert offer_success.json()["product_id"] == "PRD-NEW-1"


def test_supplier_product_rejection_flow():
    reset_db()

    make_supplier("S200", "Beta Supplier")
    create_user("admin_user", "admin@test.com", "pass123", UserRole.ADMIN, name="Admin")
    create_user("supplier_beta", "beta@test.com", "pass123", UserRole.SUPPLIER, supplier_id="S200", name="Beta")

    admin_token = login("admin_user", "pass123")
    supplier_token = login("supplier_beta", "pass123")

    # 1. Supplier submits product
    client.post(
        "/api/products",
        headers={"Authorization": f"Bearer {supplier_token}"},
        json={
            "product_id": "PRD-REJ-1",
            "name": "Overpriced Sensor",
            "category": "Sensors",
            "unit_cost": 5000.0,
            "status": "ACTIVE",
        },
    )

    # 2. Admin rejects product with reason
    rej_resp = client.patch(
        "/api/products/PRD-REJ-1/reject",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"reason": "Cost is above market standard"},
    )
    assert rej_resp.status_code == 200
    rej_data = rej_resp.json()
    assert rej_data["approval_status"] == "REJECTED"
    assert rej_data["rejection_reason"] == "Cost is above market standard"

    # 3. Supplier CANNOT create offer on rejected product
    offer_attempt = client.post(
        "/api/offers",
        headers={"Authorization": f"Bearer {supplier_token}"},
        json={
            "product_id": "PRD-REJ-1",
            "quantity": 10,
            "unit_price": 5000.0,
            "delivery_days": 3,
            "valid_until": "2030-01-01T00:00:00",
        },
    )
    assert offer_attempt.status_code == 400
    assert "not approved" in offer_attempt.json()["detail"].lower()

    # Re-seed standard data for local development/server
    seed_standard_data()


def test_auto_generated_product_id():
    reset_db()

    make_supplier("S300", "Gamma Supplier")
    create_user("supplier_gamma", "gamma@test.com", "pass123", UserRole.SUPPLIER, supplier_id="S300", name="Gamma")
    token = login("supplier_gamma", "pass123")

    # 1. Check next-id endpoint
    next_id_resp = client.get("/api/products/next-id", headers={"Authorization": f"Bearer {token}"})
    assert next_id_resp.status_code == 200
    next_id = next_id_resp.json()["next_product_id"]
    assert next_id.startswith("P")

    # 2. Submit product without providing product_id
    create_resp1 = client.post(
        "/api/products",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Auto ID Product 1",
            "category": "Components",
            "unit_cost": 25.0,
            "status": "ACTIVE",
        },
    )
    assert create_resp1.status_code == 200, create_resp1.text
    prod1 = create_resp1.json()
    assert prod1["product_id"] == next_id
    assert prod1["approval_status"] == "PENDING"

    # 3. Submit a second product without providing product_id
    create_resp2 = client.post(
        "/api/products",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Auto ID Product 2",
            "category": "Components",
            "unit_cost": 35.0,
            "status": "ACTIVE",
        },
    )
    assert create_resp2.status_code == 200, create_resp2.text
    prod2 = create_resp2.json()
    assert prod2["product_id"] != prod1["product_id"]
    assert prod2["product_id"].startswith("P")

    seed_standard_data()

