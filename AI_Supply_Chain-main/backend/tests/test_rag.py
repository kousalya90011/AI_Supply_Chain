from __future__ import annotations

from datetime import datetime, timezone, timedelta
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
from app.query.scope import QueryScope
from app.services.query_service import QueryService
from app.rag.document_builder import KnowledgeDocumentBuilder
from app.rag.semantic_retriever import SemanticRetriever
from app.rag.structured_retriever import StructuredRetriever
from app.rag.schemas import EvidenceItem, KnowledgeDocument

client = TestClient(app)


def setup_module():
    db = SessionLocal()
    try:
        db.query(SupplierOffer).delete()
        db.query(Order).delete()
        db.query(Product).delete()
        db.query(Supplier).delete()
        db.query(User).delete()
        db.query(AuditTrace).delete()
        db.commit()

        # Suppliers
        s1 = Supplier(supplier_id="S001", name="Alpha Supply", region="NA", tier="GOLD", status="ACTIVE")
        s2 = Supplier(supplier_id="S002", name="Beta Tech", region="EU", tier="SILVER", status="ACTIVE")
        db.add_all([s1, s2])

        # Products
        p1 = Product(product_id="P00001", name="Alpha Component", category="Electronics", unit_cost=50.0, status="ACTIVE")
        p2 = Product(product_id="P00002", name="Beta Widget", category="Electronics", unit_cost=100.0, status="ACTIVE")
        p3 = Product(product_id="P00003", name="Consumer Gadget", category="Consumer", unit_cost=53.38, status="ACTIVE")
        db.add_all([p1, p2, p3])

        # Users
        u_admin = User(username="admin_user", email="admin@scm.test", password_hash=get_password_hash("AdminPass123!"), role=UserRole.ADMIN.value, is_active=True)
        u_sup1 = User(username="supplier_user1", email="sup1@scm.test", password_hash=get_password_hash("SupplierPass123!"), role=UserRole.SUPPLIER.value, supplier_id="S001", is_active=True)
        u_sup2 = User(username="supplier_user2", email="sup2@scm.test", password_hash=get_password_hash("SupplierPass123!"), role=UserRole.SUPPLIER.value, supplier_id="S002", is_active=True)
        db.add_all([u_admin, u_sup1, u_sup2])

        # Offers
        now = datetime.now(timezone.utc)
        o1 = SupplierOffer(supplier_id="S001", product_id="P00001", quantity=100, unit_price=45.0, delivery_days=5, status="PENDING", valid_until=now + timedelta(days=30))
        o2 = SupplierOffer(supplier_id="S002", product_id="P00002", quantity=200, unit_price=90.0, delivery_days=8, status="PENDING", valid_until=now + timedelta(days=30))
        db.add_all([o1, o2])

        db.commit()
    finally:
        db.close()


def get_token(username: str) -> str:
    password = "AdminPass123!" if "admin" in username else "SupplierPass123!"
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


# =============================================================
# 1. Product knowledge document generation
# =============================================================
def test_1_product_knowledge_document_generation():
    builder = KnowledgeDocumentBuilder()
    db = SessionLocal()
    try:
        docs = builder.build_product_documents(db=db)
        assert len(docs) > 0
        # Check P00003 specifically
        p3_docs = [d for d in docs if d.entity_id == "P00003"]
        assert len(p3_docs) == 1
        p3 = p3_docs[0]
        assert p3.doc_type == "product"
        assert p3.entity_id == "P00003"
        assert "Operational Risk Profile" in p3.content or "Operational Risk Profile" in p3.title
        assert "Category" in p3.content
        assert "unit_cost" in p3.metadata
        assert "supplier_ids" in p3.metadata
    finally:
        db.close()


# =============================================================
# 2. Supplier knowledge document generation
# =============================================================
def test_2_supplier_knowledge_document_generation():
    builder = KnowledgeDocumentBuilder()
    db = SessionLocal()
    try:
        docs = builder.build_supplier_documents(db=db)
        assert len(docs) > 0
        # Check that suppliers contain operational metrics and offers
        s_doc = docs[0]
        assert s_doc.doc_type == "supplier"
        assert s_doc.entity_id.startswith("S")
        assert "Performance & Relationship Profile" in s_doc.content or "Performance & Relationship Profile" in s_doc.title
        assert "late_rate" in s_doc.metadata
        assert "product_ids" in s_doc.metadata
    finally:
        db.close()


# =============================================================
# 3. Structured exact lookup
# =============================================================
def test_3_structured_exact_lookup():
    qs = QueryService()
    res = qs.query("Who supplies P00003?")
    assert res["status"] == "success"
    assert res["retrieval_mode"] == "structured"
    assert len(res["evidence"]) > 0
    for ev in res["evidence"]:
        assert ev.get("retrieval_method") == "structured"
        assert ev.get("source_type") in {"analytics", "database"}
    assert "Supplier relationships identified" in res["answer"]
    assert "Evidence:" in res["answer"]
    assert "Sources:" in res["answer"]


# =============================================================
# 4. Semantic product retrieval
# =============================================================
def test_4_semantic_product_retrieval():
    sr = SemanticRetriever()
    res = sr.retrieve("Summarize the risk profile of P00003.", doc_type="product", target_entity_id="P00003")
    assert res.retrieval_mode == "semantic"
    assert len(res.documents) > 0
    assert res.documents[0].doc_type == "product"
    assert res.documents[0].entity_id == "P00003"
    assert len(res.evidence) > 0
    assert res.evidence[0]["retrieval_method"] == "semantic"
    assert res.evidence[0]["source_type"] == "knowledge_base"


# =============================================================
# 5. Semantic supplier retrieval
# =============================================================
def test_5_semantic_supplier_retrieval():
    sr = SemanticRetriever()
    res = sr.retrieve("What should I know about supplier S0001?", doc_type="supplier", target_entity_id="S0001")
    assert res.retrieval_mode == "semantic"
    assert len(res.documents) > 0
    assert res.documents[0].doc_type == "supplier"
    assert res.documents[0].entity_id in {"S0001", "S001"}


# =============================================================
# 6. Hybrid retrieval
# =============================================================
def test_6_hybrid_retrieval():
    qs = QueryService()
    query = "Which suppliers have high delivery risk, what products do they supply, and how is demand and inventory for those products?"
    res = qs.query(query)
    assert res["status"] == "success"
    assert res["retrieval_mode"] == "hybrid"
    assert len(res["sources"]) >= 2
    # Verify both structured and semantic evidence exist
    methods = {e.get("retrieval_method") for e in res["evidence"]}
    assert "structured" in methods
    assert "semantic" in methods
    assert "Evidence:" in res["answer"]
    assert "Sources:" in res["answer"]


# =============================================================
# 7. Supplier RBAC filtering
# =============================================================
def test_7_supplier_rbac_filtering():
    s001_scope = QueryScope(username="supplier_user1", role="SUPPLIER", supplier_id="S001", scope_type="SUPPLIER_ONLY")
    qs = QueryService()
    res = qs.query("Which products do I supply?", user_scope=s001_scope)
    assert res["status"] == "success"
    assert res["authorized_scope"] == "supplier:S001"
    # Ensure no evidence belongs to S002
    for ev in res["evidence"]:
        sid = ev.get("entity_id") if ev.get("entity_type") == "supplier" else ev.get("data", {}).get("supplier_id")
        if sid:
            assert sid in {"S001", "S0001", "S1"}


# =============================================================
# 8. Supplier cannot retrieve another supplier's document
# =============================================================
def test_8_supplier_cannot_retrieve_another_supplier_document():
    s001_scope = QueryScope(username="supplier_user1", role="SUPPLIER", supplier_id="S001", scope_type="SUPPLIER_ONLY")
    qs = QueryService()
    res = qs.query("What should I know about supplier S002?", user_scope=s001_scope)
    assert res["status"] == "denied"
    assert len(res["evidence"]) == 0
    assert "Access denied" in res["answer"]

    # Direct vector store search with S001 user scope must exclude S002 documents prior to scoring
    sr = SemanticRetriever()
    direct_res = sr.retrieve("What should I know about supplier S002?", user_scope=s001_scope, target_entity_id="S002")
    assert len(direct_res.documents) == 0
    assert len(direct_res.evidence) == 0


# =============================================================
# 9. Cross-domain retrieval remains authorized
# =============================================================
def test_9_cross_domain_retrieval_remains_authorized():
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
    assert "retrieval_mode" in body
    assert "sources" in body
    for ev in body.get("evidence", []):
        sid = ev.get("data", {}).get("supplier_id")
        if sid:
            assert sid in {"S001", "S0001", "S1"}


# =============================================================
# 10. LLM receives only authorized evidence
# =============================================================
def test_10_llm_receives_only_authorized_evidence():
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
        assert mock_insight.call_count == 0
        for call_args in mock_llm.call_args_list:
            messages = call_args.kwargs.get("messages") or (call_args.args[0] if call_args.args else [])
            for msg in messages:
                content = str(msg.get("content", ""))
                assert "Beta Tech" not in content
                assert "evidence" not in content.lower()


# =============================================================
# 11. Structured fallback works if vector retrieval fails
# =============================================================
def test_11_structured_fallback_works_if_vector_retrieval_fails():
    qs = QueryService()
    with patch("app.rag.semantic_retriever.SemanticRetriever.retrieve", side_effect=RuntimeError("Vector Store Offline")):
        # Query that would normally use semantic retrieval falls back to structured safely
        res = qs.query("Summarize the risk profile of P00003.")
        assert res["status"] == "success"
        # Since semantic failed, retrieval mode is structured
        assert res["retrieval_mode"] == "structured"
        assert len(res["evidence"]) > 0
        assert "risk_score" in str(res["evidence"])


# =============================================================
# 12. Evidence model consistency (Requirement 13)
# =============================================================
def test_12_evidence_model_consistency():
    qs = QueryService()
    res = qs.query("Summarize the risk profile of P00003.")
    assert len(res["evidence"]) > 0
    for ev in res["evidence"]:
        assert "source_type" in ev
        assert "source_id" in ev
        assert "entity_type" in ev
        assert "entity_id" in ev
        assert "metric" in ev
        assert "value" in ev
        assert "retrieval_method" in ev
        assert ev["retrieval_method"] in {"structured", "semantic"}
