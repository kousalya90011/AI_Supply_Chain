from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.database import SessionLocal
from app.models.entities import User, Supplier, Product, SupplierOffer, Order, AuditTrace, UserRole
from app.services.auth_service import get_password_hash

client = TestClient(app)


def reset_db():
    db = SessionLocal()
    try:
        db.query(SupplierOffer).delete()
        db.query(Order).delete()
        db.query(Product).delete()
        db.query(Supplier).delete()
        db.query(User).delete()
        db.query(AuditTrace).delete()
        db.commit()
    finally:
        db.close()


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


def make_supplier(supplier_id, name, region="NA"):
    db = SessionLocal()
    try:
        s = Supplier(
            supplier_id=supplier_id,
            name=name,
            region=region,
            tier="GOLD",
            status="ACTIVE",
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        return s
    finally:
        db.close()


def make_product(product_id, name, category="Electronics", unit_cost=100.0):
    db = SessionLocal()
    try:
        p = Product(
            product_id=product_id,
            name=name,
            category=category,
            unit_cost=unit_cost,
            status="ACTIVE",
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        return p
    finally:
        db.close()


def test_1_and_2_admin_can_create_supplier_and_product():
    reset_db()
    create_user("admin", "admin@example.com", "admin123", UserRole.ADMIN, name="Admin")
    admin_token = login("admin", "admin123")

    # 1. Admin can create supplier
    sup_resp = client.post(
        "/api/suppliers",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "supplier_id": "S001",
            "name": "Supplier One",
            "region": "North America",
            "tier": "TIER_1",
            "status": "ACTIVE",
        },
    )
    assert sup_resp.status_code == 200, sup_resp.text
    assert sup_resp.json()["supplier_id"] == "S001"

    # 2. Admin can create product
    prod_resp = client.post(
        "/api/products",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "product_id": "P001",
            "name": "Component Alpha",
            "category": "Electronics",
            "unit_cost": 150.0,
            "status": "ACTIVE",
        },
    )
    assert prod_resp.status_code == 200, prod_resp.text
    assert prod_resp.json()["product_id"] == "P001"


def test_3_4_5_supplier_creates_offer_starts_pending_and_viewable():
    reset_db()
    make_supplier("S001", "Supplier Alpha")
    make_product("P001", "Widget A")
    create_user("supplier_alpha", "alpha@example.com", "pw123", UserRole.SUPPLIER, supplier_id="S001", name="Alpha")

    token = login("supplier_alpha", "pw123")

    # 3. Supplier S001 can create offer (backend derives supplier_id)
    create_resp = client.post(
        "/api/offers",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "product_id": "P001",
            "quantity": 100,
            "unit_price": 125.50,
            "delivery_days": 7,
            "valid_until": "2030-10-10T00:00:00",
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    offer_data = create_resp.json()

    # 4. Offer starts as PENDING and supplier_id is derived
    assert offer_data["status"] == "PENDING"
    assert offer_data["supplier_id"] == "S001"
    assert offer_data["product_id"] == "P001"
    assert offer_data["quantity"] == 100
    assert offer_data["unit_price"] == 125.50

    offer_id = offer_data["offer_id"]

    # 5. Supplier S001 can view the offer
    view_resp = client.get(
        f"/api/offers/{offer_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert view_resp.status_code == 200
    assert view_resp.json()["offer_id"] == offer_id

    list_resp = client.get(
        "/api/offers",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_resp.status_code == 200
    offers = list_resp.json()
    assert any(o["offer_id"] == offer_id for o in offers)


def test_6_supplier_cannot_access_other_supplier_offer():
    reset_db()
    make_supplier("S001", "Supplier Alpha")
    make_supplier("S002", "Supplier Beta")
    make_product("P001", "Widget A")

    create_user("supplier_alpha", "alpha@example.com", "pw123", UserRole.SUPPLIER, supplier_id="S001", name="Alpha")
    create_user("supplier_beta", "beta@example.com", "pw123", UserRole.SUPPLIER, supplier_id="S002", name="Beta")

    alpha_token = login("supplier_alpha", "pw123")
    beta_token = login("supplier_beta", "pw123")

    # Beta creates an offer
    beta_create = client.post(
        "/api/offers",
        headers={"Authorization": f"Bearer {beta_token}"},
        json={
            "product_id": "P001",
            "quantity": 50,
            "unit_price": 99.0,
            "delivery_days": 3,
            "valid_until": "2030-10-10T00:00:00",
        },
    )
    assert beta_create.status_code == 200
    beta_offer_id = beta_create.json()["offer_id"]

    # 6. Supplier S001 cannot access S002's offer by ID
    blocked_get = client.get(
        f"/api/offers/{beta_offer_id}",
        headers={"Authorization": f"Bearer {alpha_token}"},
    )
    assert blocked_get.status_code == 403

    # Supplier S001 cannot query S002's offers list
    blocked_list = client.get(
        "/api/offers?supplier_id=S002",
        headers={"Authorization": f"Bearer {alpha_token}"},
    )
    assert blocked_list.status_code == 403


def test_7_supplier_cannot_accept_or_reject_offer():
    reset_db()
    make_supplier("S001", "Supplier Alpha")
    make_product("P001", "Widget A")
    create_user("supplier_alpha", "alpha@example.com", "pw123", UserRole.SUPPLIER, supplier_id="S001", name="Alpha")

    token = login("supplier_alpha", "pw123")

    create_resp = client.post(
        "/api/offers",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "product_id": "P001",
            "quantity": 30,
            "unit_price": 105.0,
            "delivery_days": 4,
            "valid_until": "2030-10-10T00:00:00",
        },
    )
    offer_id = create_resp.json()["offer_id"]

    # 7. Supplier cannot accept an offer
    accept_resp = client.patch(
        f"/api/offers/{offer_id}/accept",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert accept_resp.status_code == 403

    # Supplier cannot reject an offer
    reject_resp = client.patch(
        f"/api/offers/{offer_id}/reject",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert reject_resp.status_code == 403


def test_8_9_10_11_12_manager_views_and_accepts_offer_creates_order_and_audit():
    reset_db()
    make_supplier("S001", "Supplier Alpha")
    make_product("P001", "Widget A")
    create_user("supplier_alpha", "alpha@example.com", "pw123", UserRole.SUPPLIER, supplier_id="S001", name="Alpha")
    create_user("manager_1", "manager@example.com", "pw123", UserRole.SUPPLY_CHAIN_MANAGER, name="Manager")

    supplier_token = login("supplier_alpha", "pw123")
    manager_token = login("manager_1", "pw123")

    create_resp = client.post(
        "/api/offers",
        headers={"Authorization": f"Bearer {supplier_token}"},
        json={
            "product_id": "P001",
            "quantity": 75,
            "unit_price": 110.0,
            "delivery_days": 5,
            "valid_until": "2030-12-31T00:00:00",
        },
    )
    offer_id = create_resp.json()["offer_id"]

    # 8. Manager can view pending offer
    mgr_view = client.get(
        f"/api/offers/{offer_id}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert mgr_view.status_code == 200
    assert mgr_view.json()["status"] == "PENDING"

    mgr_list = client.get(
        "/api/offers?status=PENDING&supplier_id=S001&product_id=P001",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert mgr_list.status_code == 200
    assert any(o["offer_id"] == offer_id for o in mgr_list.json())

    # 9. Manager accepts offer
    accept_resp = client.patch(
        f"/api/offers/{offer_id}/accept",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert accept_resp.status_code == 200, accept_resp.text
    payload = accept_resp.json()

    # 10. Offer becomes ACCEPTED
    assert payload["offer"]["status"] == "ACCEPTED"
    assert payload["offer"]["reviewed_by"] == "manager_1"
    assert payload["offer"]["reviewed_at"] is not None

    # 11. Corresponding order is created
    order = payload["order"]
    assert order["supplier_id"] == "S001"
    assert order["product_id"] == "P001"
    assert order["quantity"] == 75
    assert order["unit_price"] == 110.0
    assert order["status"] == "PENDING"

    # 12. Audit event exists
    db = SessionLocal()
    try:
        audits = db.query(AuditTrace).order_by(AuditTrace.id.desc()).limit(5).all()
        audit_queries = [a.query for a in audits]
        assert "OFFER_ACCEPTED" in audit_queries or any("offer" in (a.query or "").lower() for a in audits)
        assert "ORDER_CREATED" in audit_queries
        accept_audit = next(a for a in audits if a.query == "OFFER_ACCEPTED")
        assert accept_audit.agent_name == "manager_1"
    finally:
        db.close()


def test_13_supplier_cannot_modify_another_suppliers_order():
    reset_db()
    make_supplier("S001", "Supplier Alpha")
    make_supplier("S002", "Supplier Beta")
    make_product("P001", "Widget A")
    create_user("supplier_alpha", "alpha@example.com", "pw123", UserRole.SUPPLIER, supplier_id="S001", name="Alpha")
    create_user("admin", "admin@example.com", "admin123", UserRole.ADMIN, name="Admin")

    admin_token = login("admin", "admin123")
    alpha_token = login("supplier_alpha", "pw123")

    # Create order for S002
    order_resp = client.post(
        "/api/orders",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "supplier_id": "S002",
            "product_id": "P001",
            "quantity": 20,
            "unit_price": 50.0,
            "status": "PENDING",
        },
    )
    assert order_resp.status_code == 200
    s002_order_id = order_resp.json()["order_id"]

    # 13. Supplier S001 cannot modify S002's order
    modify_resp = client.put(
        f"/api/orders/{s002_order_id}",
        headers={"Authorization": f"Bearer {alpha_token}"},
        json={"status": "DELIVERED"},
    )
    assert modify_resp.status_code == 403

    # S001 cannot view S002's order
    view_resp = client.get(
        f"/api/orders/{s002_order_id}",
        headers={"Authorization": f"Bearer {alpha_token}"},
    )
    assert view_resp.status_code == 403


def test_14_manager_cannot_manage_users_but_admin_can():
    reset_db()
    create_user("manager_1", "manager@example.com", "pw123", UserRole.SUPPLY_CHAIN_MANAGER, name="Manager")
    create_user("admin", "admin@example.com", "admin123", UserRole.ADMIN, name="Admin")

    manager_token = login("manager_1", "pw123")
    admin_token = login("admin", "admin123")

    # 14. Manager cannot perform admin-only user management
    mgr_get = client.get("/api/users", headers={"Authorization": f"Bearer {manager_token}"})
    assert mgr_get.status_code == 403

    mgr_post = client.post(
        "/api/users",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"username": "newuser", "email": "new@example.com", "password": "password123", "name": "New"},
    )
    assert mgr_post.status_code == 403

    admin_get = client.get("/api/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_get.status_code == 200


def test_15_failed_order_creation_rolls_back_offer_acceptance():
    reset_db()
    make_supplier("S001", "Supplier Alpha")
    make_product("P001", "Widget A")
    create_user("supplier_alpha", "alpha@example.com", "pw123", UserRole.SUPPLIER, supplier_id="S001", name="Alpha")
    create_user("manager_1", "manager@example.com", "pw123", UserRole.SUPPLY_CHAIN_MANAGER, name="Manager")

    supplier_token = login("supplier_alpha", "pw123")
    manager_token = login("manager_1", "pw123")

    create_resp = client.post(
        "/api/offers",
        headers={"Authorization": f"Bearer {supplier_token}"},
        json={
            "product_id": "P001",
            "quantity": 10,
            "unit_price": 40.0,
            "delivery_days": 2,
            "valid_until": "2030-10-10T00:00:00",
        },
    )
    offer_id = create_resp.json()["offer_id"]

    # Simulate failure during Order creation / saving in database
    with patch("app.api.offers.Order", side_effect=RuntimeError("Database constraint failure during order creation")):
        accept_resp = client.patch(
            f"/api/offers/{offer_id}/accept",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert accept_resp.status_code == 500

    # 15. Verify rollback: offer status must NOT remain ACCEPTED; must still be PENDING
    db = SessionLocal()
    try:
        offer_in_db = db.query(SupplierOffer).filter(SupplierOffer.offer_id == offer_id).first()
        assert offer_in_db is not None
        assert offer_in_db.status == "PENDING"
        assert offer_in_db.reviewed_by is None
        assert offer_in_db.reviewed_at is None

        # Verify no order was created
        orders_in_db = db.query(Order).filter(Order.supplier_id == "S001").all()
        assert len(orders_in_db) == 0
    finally:
        db.close()


def test_offer_lifecycle_edit_withdraw_reject():
    reset_db()
    make_supplier("S001", "Supplier Alpha")
    make_product("P001", "Widget A")
    create_user("supplier_alpha", "alpha@example.com", "pw123", UserRole.SUPPLIER, supplier_id="S001", name="Alpha")
    create_user("manager_1", "manager@example.com", "pw123", UserRole.SUPPLY_CHAIN_MANAGER, name="Manager")

    supplier_token = login("supplier_alpha", "pw123")
    manager_token = login("manager_1", "pw123")

    # Supplier creates offer
    create_resp = client.post(
        "/api/offers",
        headers={"Authorization": f"Bearer {supplier_token}"},
        json={
            "product_id": "P001",
            "quantity": 20,
            "unit_price": 100.0,
            "delivery_days": 5,
            "valid_until": "2030-10-10T00:00:00",
        },
    )
    offer_id = create_resp.json()["offer_id"]

    # Supplier edits own pending offer
    edit_resp = client.put(
        f"/api/offers/{offer_id}",
        headers={"Authorization": f"Bearer {supplier_token}"},
        json={"quantity": 25, "unit_price": 95.0},
    )
    assert edit_resp.status_code == 200
    assert edit_resp.json()["quantity"] == 25
    assert edit_resp.json()["unit_price"] == 95.0

    # Supplier withdraws own pending offer
    withdraw_resp = client.patch(
        f"/api/offers/{offer_id}/withdraw",
        headers={"Authorization": f"Bearer {supplier_token}"},
    )
    assert withdraw_resp.status_code == 200
    assert withdraw_resp.json()["status"] == "WITHDRAWN"

    # Cannot withdraw or edit again once withdrawn
    withdraw_again = client.patch(
        f"/api/offers/{offer_id}/withdraw",
        headers={"Authorization": f"Bearer {supplier_token}"},
    )
    assert withdraw_again.status_code == 400

    edit_again = client.put(
        f"/api/offers/{offer_id}",
        headers={"Authorization": f"Bearer {supplier_token}"},
        json={"quantity": 30},
    )
    assert edit_again.status_code == 400

    # Manager rejects another pending offer
    create_resp2 = client.post(
        "/api/offers",
        headers={"Authorization": f"Bearer {supplier_token}"},
        json={
            "product_id": "P001",
            "quantity": 10,
            "unit_price": 100.0,
            "delivery_days": 2,
            "valid_until": "2030-10-10T00:00:00",
        },
    )
    offer_id_2 = create_resp2.json()["offer_id"]

    reject_resp = client.patch(
        f"/api/offers/{offer_id_2}/reject",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "REJECTED"
    assert reject_resp.json()["reviewed_by"] == "manager_1"
