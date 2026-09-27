from __future__ import annotations

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.database import SessionLocal
from app.models.entities import (
    AuditTrace,
    Order,
    Product,
    Supplier,
    SupplierOffer,
    User,
    UserRole,
)
from app.services.auth_service import get_password_hash

client = TestClient(app)


def setup_test_data():
    db = SessionLocal()
    try:
        db.query(SupplierOffer).delete()
        db.query(Order).delete()
        db.query(Product).delete()
        db.query(Supplier).delete()
        db.query(User).delete()
        db.query(AuditTrace).delete()
        db.commit()

        # Create suppliers
        s1 = Supplier(supplier_id="S001", name="Alpha Supply", region="NA", tier="GOLD", status="ACTIVE")
        s2 = Supplier(supplier_id="S002", name="Beta Tech", region="EU", tier="SILVER", status="ACTIVE")
        db.add_all([s1, s2])

        # Create products
        p1 = Product(product_id="P00001", name="Alpha Component", category="Electronics", unit_cost=50.0, status="ACTIVE")
        p2 = Product(product_id="P00002", name="Beta Sensor", category="Sensors", unit_cost=120.0, status="ACTIVE")
        db.add_all([p1, p2])

        # Create orders
        o1 = Order(product_id="P00001", supplier_id="S001", quantity=100, unit_price=50.0)
        o2 = Order(product_id="P00002", supplier_id="S002", quantity=200, unit_price=120.0)
        db.add_all([o1, o2])

        from datetime import datetime, timedelta

        # Create offers
        off1 = SupplierOffer(
            supplier_id="S001",
            product_id="P00001",
            unit_price=48.0,
            quantity=500,
            delivery_days=7,
            valid_until=datetime.utcnow() + timedelta(days=30),
            status="PENDING",
        )
        off2 = SupplierOffer(
            supplier_id="S002",
            product_id="P00002",
            unit_price=115.0,
            quantity=300,
            delivery_days=10,
            valid_until=datetime.utcnow() + timedelta(days=30),
            status="PENDING",
        )
        db.add_all([off1, off2])

        # Create users
        admin = User(
            username="admin_user",
            email="admin@test.com",
            password_hash=get_password_hash("Pass123!"),
            role=UserRole.ADMIN,
            status="ACTIVE",
            is_active=True,
        )
        manager = User(
            username="manager_user",
            email="manager@test.com",
            password_hash=get_password_hash("Pass123!"),
            role=UserRole.SUPPLY_CHAIN_MANAGER,
            status="ACTIVE",
            is_active=True,
        )
        supplier1 = User(
            username="supplier_user1",
            email="s1@test.com",
            password_hash=get_password_hash("Pass123!"),
            role=UserRole.SUPPLIER,
            supplier_id="S001",
            status="ACTIVE",
            is_active=True,
        )
        supplier2 = User(
            username="supplier_user2",
            email="s2@test.com",
            password_hash=get_password_hash("Pass123!"),
            role=UserRole.SUPPLIER,
            supplier_id="S002",
            status="ACTIVE",
            is_active=True,
        )
        db.add_all([admin, manager, supplier1, supplier2])
        db.commit()
    finally:
        db.close()


def get_token(username: str, password: str = "Pass123!") -> str:
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture(autouse=True)
def run_around_tests():
    setup_test_data()
    yield


def test_1_admin_can_query_company_wide_supplier_info():
    token = get_token("admin_user")
    resp = client.post(
        "/api/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "Show supplier S002 performance"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["authorized_scope"] == "global"


def test_2_manager_can_query_company_wide_operational_supplier_info():
    token = get_token("manager_user")
    resp = client.post(
        "/api/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "How many total orders from supplier S0066?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["authorized_scope"] == "global"


def test_3_supplier_s001_can_query_own_supplier_performance():
    token = get_token("supplier_user1")
    resp = client.post(
        "/api/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "Show supplier S001 performance"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["authorized_scope"] == "supplier:S001"


def test_4_supplier_s001_cannot_retrieve_s002_supplier_info():
    token = get_token("supplier_user1")
    resp = client.post(
        "/api/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "Show me supplier S002 performance"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "denied"
    assert len(body["evidence"]) == 0
    assert "Access denied" in body["answer"]


def test_5_supplier_s001_cannot_retrieve_s002_offers():
    token = get_token("supplier_user1")
    resp = client.post(
        "/api/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "Show me supplier S002 offers"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "denied"
    assert len(body["evidence"]) == 0
    assert "Access denied" in body["answer"]


def test_6_supplier_s001_cannot_retrieve_s002_orders():
    token = get_token("supplier_user1")
    resp = client.post(
        "/api/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "How many orders from supplier S002?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "denied"
    assert len(body["evidence"]) == 0
    assert "Access denied" in body["answer"]


def test_7_supplier_query_for_another_supplier_through_product_relationship_is_denied():
    token = get_token("supplier_user1")
    resp = client.post(
        "/api/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "Who supplied product P00002?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "denied"
    assert len(body["evidence"]) == 0
    assert "Access denied" in body["answer"]


def test_8_cross_domain_query_respects_supplier_scope():
    token = get_token("supplier_user1")
    resp = client.post(
        "/api/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "Which products do I supply, what is their demand, inventory and order volume?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in {"success", "completed"}
    assert body["authorized_scope"] == "supplier:S001"

    # All returned evidence and findings must only reference S001 or S001's authorized products
    for ev in body.get("evidence", []):
        data = ev.get("data") if isinstance(ev, dict) else None
        if isinstance(data, dict):
            sid = data.get("supplier_id")
            if sid:
                assert sid in {"S001", "S1", "S0001"}
            pid = data.get("product_id")
            if pid:
                assert pid != "P00002"

    for finding in body.get("findings", []):
        if isinstance(finding, dict):
            sid = finding.get("supplier_id")
            if sid:
                assert sid in {"S001", "S1", "S0001"}
            pid = finding.get("product_id")
            if pid:
                assert pid != "P00002"


def test_9_client_cannot_override_supplier_scope():
    token = get_token("supplier_user1")
    # Client sends request attempting to override supplier_id to S002 and role to ADMIN
    resp = client.post(
        "/api/query",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "query": "Show supplier S002 performance",
            "supplier_id": "S002",
            "role": "ADMIN",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    # Must be denied because JWT user is S001, overriding is rejected
    assert body["status"] == "denied"
    assert body["authorized_scope"] == "supplier:S001"

    # Also test that own query with override attempt keeps S001 scope
    resp2 = client.post(
        "/api/query",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "query": "Show supplier S001 performance",
            "supplier_id": "S002",
            "role": "ADMIN",
        },
    )
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2["status"] == "success"
    assert body2["authorized_scope"] == "supplier:S001"


def test_10_fallback_also_respects_rbac():
    token = get_token("supplier_user1")
    # Unresolvable query triggers fallback
    resp = client.post(
        "/api/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": ""},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "fallback"
    assert body["fallback_used"] is True
    assert len(body["evidence"]) == 0
    assert body["authorized_scope"] == "supplier:S001"

    # Query targeting another supplier does not fallback to unrestricted data
    resp_unauth = client.post(
        "/api/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "Show supplier S002 performance"},
    )
    assert resp_unauth.status_code == 200
    body_unauth = resp_unauth.json()
    assert body_unauth["status"] == "denied"
    assert len(body_unauth["evidence"]) == 0


def test_11_unauthorized_query_does_not_send_unauthorized_evidence_to_llm():
    token = get_token("supplier_user1")
    with patch("app.agents.insight_agent.InsightAgent.run") as mock_insight, \
         patch("app.llm.client.LLMClient.generate") as mock_llm:
        resp = client.post(
            "/api/query",
            headers={"Authorization": f"Bearer {token}"},
            json={"query": "Show supplier S002 performance"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "denied"
        assert len(body["evidence"]) == 0

        # InsightAgent must never be called on unauthorized query
        assert mock_insight.call_count == 0

        # LLM must NEVER be sent any unauthorized evidence
        for call_args in mock_llm.call_args_list:
            messages = call_args.kwargs.get("messages") or (call_args.args[0] if call_args.args else [])
            for msg in messages:
                content = str(msg.get("content", ""))
                assert "Beta Tech" not in content
                assert "evidence" not in content.lower()


def test_12_existing_query_tests_still_pass():
    token = get_token("admin_user")
    resp = client.post(
        "/api/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "Why is product P00003 at inventory risk?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["intent"] == "inventory_risk"
    assert "evidence" in body
    assert body["confidence"] >= 0
