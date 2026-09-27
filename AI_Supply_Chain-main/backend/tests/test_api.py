from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root():
    response = client.get("/")

    assert response.status_code == 200

    body = response.json()

    assert "application" in body
    assert body["status"] == "running"


def test_data_status():
    response = client.get("/api/data/status")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "success"
    assert "datasets" in body


def test_dashboard():
    response = client.get("/api/analytics/dashboard")

    assert response.status_code == 200

    body = response.json()

    assert "total_orders" in body
    assert "late_orders" in body


def test_routing_evaluation():
    response = client.get("/api/evaluation/routing")

    assert response.status_code == 200

    body = response.json()

    assert 0 <= body["intent_accuracy"] <= 1


def test_evaluation_summary():
    response = client.get("/api/evaluation/summary")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "success"


def test_audit_endpoint():
    response = client.get("/api/audit/recent")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "success"


def test_query():
    response = client.post(
        "/api/query",
        json={
            "query": "Why is product P00003 at inventory risk?"
        }
    )

    assert response.status_code == 200

    body = response.json()

    assert body["intent"] == "inventory_risk"
    assert body["confidence"] >= 0
    assert "evidence" in body


def test_price_ranking_with_supplier_lookup():
    response = client.post(
        "/api/query",
        json={
            "query": "what are the top products as per price and who supplies them?"
        }
    )

    assert response.status_code == 200

    body = response.json()

    assert body["requirement_count"] >= 2
    assert any(
        item.get("requirement", {}).get("metric") == "product_supplier"
        or item.get("metric") == "product_supplier"
        for item in body["requirement_results"]
    )


def test_supplier_lookup_returns_real_findings_for_top_price_products():
    response = client.post(
        "/api/query",
        json={
            "query": "what are the top products as per price and who supplies them?"
        }
    )

    assert response.status_code == 200

    body = response.json()
    supplier_result = next(
        (
            item for item in body["requirement_results"]
            if item.get("metric") == "product_supplier"
            or item.get("requirement", {}).get("metric") == "product_supplier"
        ),
        None,
    )

    assert supplier_result is not None
    assert supplier_result["status"] == "success"
    assert supplier_result["findings"]
    assert any(
        "supplier_id" in finding and "product_id" in finding
        for finding in supplier_result["findings"]
    )


def test_who_supplied_product_lookup():
    response = client.post(
        "/api/query",
        json={
            "query": "Who supplied product P00003?"
        }
    )

    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "success"
    assert body["intent"] == "supplier_relationship_analysis"
    assert body["entity_id"] == "P00003"
    assert body["requirement_count"] >= 1
    assert any(
        item.get("metric") == "product_supplier"
        or item.get("requirement", {}).get("metric") == "product_supplier"
        for item in body["requirement_results"]
    )


def test_total_orders_from_supplier_lookup():
    response = client.post(
        "/api/query",
        json={
            "query": "How many total orders from supplier S0066?"
        }
    )

    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "success"
    assert body["intent"] == "order_analysis"
    assert body["entity_id"] == "S0066"
    assert any(
        item.get("metric") == "total_orders"
        or item.get("requirement", {}).get("metric") == "total_orders"
        for item in body["requirement_results"]
    )
    assert body["answer"] and "orders" in body["answer"].lower()


def test_combined_product_supplier_total_orders_query():
    response = client.post(
        "/api/query",
        json={
            "query": "what is the demand for product P00003, who supplied it and how many total orders from this supplier?"
        }
    )

    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "success"
    assert body["requirement_count"] >= 3
    assert any(
        item.get("metric") == "total_orders"
        or item.get("requirement", {}).get("metric") == "total_orders"
        for item in body["requirement_results"]
    )
    assert any(
        item.get("metric") == "product_supplier"
        or item.get("requirement", {}).get("metric") == "product_supplier"
        for item in body["requirement_results"]
    )

    supplier_result = next(
        (
            item for item in body["requirement_results"]
            if item.get("metric") == "product_supplier"
            or item.get("requirement", {}).get("metric") == "product_supplier"
        ),
        None,
    )
    assert supplier_result is not None
    assert any(
        finding.get("product_id") == "P00003" and finding.get("supplier_id")
        for finding in supplier_result["findings"]
    )

    order_results = [
        item for item in body["requirement_results"]
        if item.get("metric") == "total_orders"
        or item.get("requirement", {}).get("metric") == "total_orders"
    ]
    assert order_results
    assert all(
        not (
            any(f.get("supplier_id") and f.get("supplier_id") != "S0066" for f in result.get("findings", []))
            and any(f.get("product_id") for f in result.get("findings", []))
        )
        for result in order_results
    )
