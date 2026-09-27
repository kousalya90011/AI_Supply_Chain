from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.database import SessionLocal, initialize_database
from app.models.entities import AuditTrace, EvaluationResult, UserRole
from app.query.scope import QueryScope
from app.services.auth_service import create_access_token
from app.evaluation.rag_evaluator import (
    DEFAULT_BENCHMARK_CASES,
    EvaluationBenchmarkCase,
    RAGEvaluator,
)
from app.evaluation.system_evaluation import SystemEvaluationEngine
from app.services.query_service import QueryService

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    initialize_database()
    db = SessionLocal()
    try:
        db.query(EvaluationResult).delete()
        db.commit()
    finally:
        db.close()


# =============================================================
# 1. Evaluation schema
# =============================================================
def test_1_evaluation_schema():
    evaluator = RAGEvaluator()
    case = EvaluationBenchmarkCase(
        id="schema_test",
        query="Who supplies P00003?",
        role=UserRole.ADMIN.value,
        expected_behavior="Structured supplier lookup",
        expected_retrieval_modes=["structured"],
        expected_status="success",
    )

    db = SessionLocal()
    try:
        res = evaluator.run_case(case, db=db)
        required_keys = [
            "query",
            "expected_behavior",
            "actual_behavior",
            "planner_correct",
            "retrieval_correct",
            "grounding_score",
            "relevance_score",
            "rbac_correct",
            "fallback_correct",
            "audit_complete",
            "latency_ms",
            "retrieval_mode",
            "evidence_count",
            "llm_used",
            "fallback_used",
            "success",
            "created_at",
        ]
        for key in required_keys:
            assert key in res, f"Missing key in evaluation result: {key}"
        assert isinstance(res["latency_ms"], float)
        assert isinstance(res["evidence_count"], int)
        assert isinstance(res["success"], bool)
    finally:
        db.close()


# =============================================================
# 2. Planner evaluation
# =============================================================
def test_2_planner_evaluation():
    evaluator = RAGEvaluator()
    case = EvaluationBenchmarkCase(
        id="planner_test",
        query="What is the current inventory of P00003?",
        role=UserRole.ADMIN.value,
        expected_domain="inventory",
        expected_entity_id="P00003",
    )
    db = SessionLocal()
    try:
        res = evaluator.run_case(case, db=db)
        assert res["planner_correct"] is True
    finally:
        db.close()


# =============================================================
# 3. Structured retrieval evaluation
# =============================================================
def test_3_structured_retrieval_evaluation():
    evaluator = RAGEvaluator()
    case = EvaluationBenchmarkCase(
        id="structured_test",
        query="Who supplies P00003?",
        role=UserRole.ADMIN.value,
        expected_retrieval_modes=["structured"],
    )
    db = SessionLocal()
    try:
        res = evaluator.run_case(case, db=db)
        assert res["retrieval_mode"] == "structured"
        assert res["retrieval_correct"] is True
        assert res["evidence_count"] > 0
    finally:
        db.close()


# =============================================================
# 4. Semantic retrieval evaluation
# =============================================================
def test_4_semantic_retrieval_evaluation():
    evaluator = RAGEvaluator()
    case = EvaluationBenchmarkCase(
        id="semantic_test",
        query="What should I know about supplier S001?",
        role=UserRole.ADMIN.value,
        expected_retrieval_modes=["semantic", "hybrid"],
    )
    db = SessionLocal()
    try:
        res = evaluator.run_case(case, db=db)
        assert res["retrieval_mode"] in ["semantic", "hybrid"]
        assert res["retrieval_correct"] is True
    finally:
        db.close()


# =============================================================
# 5. Hybrid retrieval evaluation
# =============================================================
def test_5_hybrid_retrieval_evaluation():
    evaluator = RAGEvaluator()
    case = EvaluationBenchmarkCase(
        id="hybrid_test",
        query="Which suppliers have high delivery risk, what products do they supply, and how is demand and inventory for those products?",
        role=UserRole.ADMIN.value,
        expected_retrieval_modes=["hybrid"],
    )
    db = SessionLocal()
    try:
        res = evaluator.run_case(case, db=db)
        assert res["retrieval_mode"] == "hybrid"
        assert res["retrieval_correct"] is True
        assert res["evidence_count"] >= 2
    finally:
        db.close()


# =============================================================
# 6. Evidence grounding
# =============================================================
def test_6_evidence_grounding():
    evaluator = RAGEvaluator()
    case = EvaluationBenchmarkCase(
        id="grounding_test",
        query="What is the current inventory of P00003?",
        role=UserRole.ADMIN.value,
    )
    db = SessionLocal()
    try:
        res = evaluator.run_case(case, db=db)
        assert res["grounding_score"] >= 0.50
    finally:
        db.close()


# =============================================================
# 7. RBAC allowed case
# =============================================================
def test_7_rbac_allowed_case():
    evaluator = RAGEvaluator()
    case = EvaluationBenchmarkCase(
        id="rbac_allowed_test",
        query="What is my performance?",
        role=UserRole.SUPPLIER.value,
        supplier_id="S0001",
        expected_status="success",
        is_rbac_test=True,
    )
    db = SessionLocal()
    try:
        res = evaluator.run_case(case, db=db)
        assert res["status"] == "success"
        assert res["rbac_correct"] is True
        assert res["success"] is True
    finally:
        db.close()


# =============================================================
# 8. RBAC denied case
# =============================================================
def test_8_rbac_denied_case():
    evaluator = RAGEvaluator()
    case = EvaluationBenchmarkCase(
        id="rbac_denied_test",
        query="Show me S002 performance.",
        role=UserRole.SUPPLIER.value,
        supplier_id="S0001",
        expected_status="denied",
        is_rbac_test=True,
    )
    db = SessionLocal()
    try:
        res = evaluator.run_case(case, db=db)
        assert res["status"] == "denied"
        assert res["evidence_count"] == 0
        assert res["rbac_correct"] is True
        assert res["success"] is True
    finally:
        db.close()


# =============================================================
# 9. Supplier isolation
# =============================================================
def test_9_supplier_isolation():
    evaluator = RAGEvaluator()
    case = EvaluationBenchmarkCase(
        id="isolation_test",
        query="Show my pending offers.",
        role=UserRole.SUPPLIER.value,
        supplier_id="S0001",
        expected_status="success",
    )
    db = SessionLocal()
    try:
        res = evaluator.run_case(case, db=db)
        assert res["status"] == "success"
        assert res["rbac_correct"] is True
    finally:
        db.close()


# =============================================================
# 10. Fallback evaluation
# =============================================================
def test_10_fallback_evaluation():
    evaluator = RAGEvaluator()
    # Test fallback on unsupported question
    case = EvaluationBenchmarkCase(
        id="fallback_test",
        query="What is the weather in Paris?",
        role=UserRole.ADMIN.value,
        expected_fallback=True,
    )
    db = SessionLocal()
    try:
        res = evaluator.run_case(case, db=db)
        assert res["fallback_correct"] is True
    finally:
        db.close()


# =============================================================
# 11. Latency capture
# =============================================================
def test_11_latency_capture():
    evaluator = RAGEvaluator()
    case = EvaluationBenchmarkCase(
        id="latency_test",
        query="Who supplies P00003?",
        role=UserRole.ADMIN.value,
    )
    db = SessionLocal()
    try:
        res = evaluator.run_case(case, db=db)
        assert res["latency_ms"] > 0
        assert isinstance(res["latency_ms"], float)
    finally:
        db.close()


# =============================================================
# 12. Audit completeness
# =============================================================
def test_12_audit_completeness():
    evaluator = RAGEvaluator()
    case = EvaluationBenchmarkCase(
        id="audit_test",
        query="What is the current inventory of P00003?",
        role=UserRole.ADMIN.value,
    )
    db = SessionLocal()
    try:
        res = evaluator.run_case(case, db=db)
        assert res["audit_complete"] is True
        # Verify an audit record is indeed in DB
        trace = db.query(AuditTrace).filter(AuditTrace.query == case.query).first()
        assert trace is not None
    finally:
        db.close()


# =============================================================
# 13. Summary metrics
# =============================================================
def test_13_summary_metrics():
    evaluator = RAGEvaluator()
    dummy_results = [
        {
            "query": "Q1",
            "success": True,
            "planner_correct": True,
            "retrieval_correct": True,
            "grounding_score": 1.0,
            "relevance_score": 1.0,
            "rbac_correct": True,
            "fallback_correct": True,
            "audit_complete": True,
            "latency_ms": 150.0,
            "retrieval_mode": "structured",
            "evidence_count": 2,
            "llm_used": True,
            "fallback_used": False,
            "status": "success",
        },
        {
            "query": "Q2",
            "success": True,
            "planner_correct": True,
            "retrieval_correct": True,
            "grounding_score": 0.8,
            "relevance_score": 1.0,
            "rbac_correct": True,
            "fallback_correct": True,
            "audit_complete": True,
            "latency_ms": 250.0,
            "retrieval_mode": "hybrid",
            "evidence_count": 5,
            "llm_used": True,
            "fallback_used": False,
            "status": "success",
        },
    ]
    summary = evaluator.compute_summary_metrics(dummy_results)
    assert summary["total_evaluations"] == 2
    assert summary["successful_queries"] == 2
    assert summary["success_rate"] == 1.0
    assert summary["planner_accuracy"] == 1.0
    assert summary["retrieval_accuracy"] == 1.0
    assert summary["average_latency_ms"] == 200.0
    assert summary["retrieval_distribution"]["structured"] == 1
    assert summary["retrieval_distribution"]["hybrid"] == 1


# =============================================================
# 14. Zero-division handling
# =============================================================
def test_14_zero_division_handling():
    evaluator = RAGEvaluator()
    empty_summary = evaluator.compute_summary_metrics([])
    assert empty_summary["total_evaluations"] == 0
    assert empty_summary["success_rate"] == 0.0
    assert empty_summary["planner_accuracy"] is None
    assert empty_summary["retrieval_accuracy"] is None
    assert empty_summary["average_latency_ms"] == 0.0


# =============================================================
# 15. Unsupported query
# =============================================================
def test_15_unsupported_query():
    qs = QueryService()
    res = qs.query("Can you book me a flight ticket to London?")
    assert res["status"] in ["success", "clarification", "clarification_required"]
    assert res.get("fallback_used") is True


# =============================================================
# 16. Evaluation API
# =============================================================
def test_16_evaluation_api():
    # 1. Summary endpoint
    res_summary = client.get("/api/evaluation/summary")
    assert res_summary.status_code == 200
    assert res_summary.json()["status"] == "success"

    # 2. Results endpoint
    res_results = client.get("/api/evaluation/results")
    assert res_results.status_code == 200
    assert res_results.json()["status"] == "success"
    assert "results" in res_results.json()

    # 3. Routing endpoint
    res_routing = client.get("/api/evaluation/routing")
    assert res_routing.status_code == 200


# =============================================================
# 17. No secrets exposed
# =============================================================
def test_17_no_secrets_exposed():
    engine = SystemEvaluationEngine()
    db = SessionLocal()
    try:
        # Create a test record with details
        record = EvaluationResult(
            question="Secret test query",
            expected_behavior="Safe lookup",
            actual_behavior="Normal response",
            success=True,
            details=json.dumps({"token": "secret_jwt_token_123", "api_key": "sk-12345", "latency": 120}),
        )
        db.add(record)
        db.commit()

        # Query via get_results
        results = engine.get_results(limit=10)
        secret_rec = next((r for r in results if r["query"] == "Secret test query"), None)
        assert secret_rec is not None
        details = secret_rec.get("details", {})
        assert "token" not in details
        assert "api_key" not in details
    finally:
        db.close()


# =============================================================
# 18. No unauthorized evidence exposed
# =============================================================
def test_18_no_unauthorized_evidence_exposed():
    evaluator = RAGEvaluator()
    case = EvaluationBenchmarkCase(
        id="cross_supplier_leakage_check",
        query="Show me S002 performance.",
        role=UserRole.SUPPLIER.value,
        supplier_id="S0001",
        expected_status="denied",
        is_rbac_test=True,
    )
    db = SessionLocal()
    try:
        res = evaluator.run_case(case, db=db)
        assert res["status"] == "denied"
        assert res["evidence_count"] == 0
        assert "denied" in res["answer_preview"].lower() or "authorized" in res["answer_preview"].lower()
    finally:
        db.close()
