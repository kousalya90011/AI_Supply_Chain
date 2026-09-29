"""
Comprehensive Test Suite for Business-Level Chunking, Embeddings,
Vector Store, Hybrid Retrieval, and Retrieval Evaluation.
"""

import pytest
from app.config import settings
from app.evaluation.retrieval_evaluation import RetrievalEvaluator
from app.query.schema import QueryPlan
from app.query.scope import QueryScope
from app.services.retrieval.chunking import BusinessChunkingService
from app.services.retrieval.embeddings import (
    EmbeddingProvider,
    LocalTFIDFEmbeddingProvider,
    get_embedding_provider,
)
from app.services.retrieval.hybrid_retriever import HybridRetriever
from app.services.retrieval.retrieval_models import BusinessChunk
from app.services.retrieval.semantic_retriever import SemanticRetriever
from app.services.retrieval.vector_store import LocalVectorStore
from app.services.query_service import QueryService


# =====================================================================
# 1. CHUNKING & METADATA TESTS
# =====================================================================
def test_1_supplier_chunking_and_metadata():
    chunk = BusinessChunkingService.create_supplier_chunk(
        supplier_id="SUP001",
        supplier_name="Global Logistics SUP001",
        risk_score=72.4,
        risk_level="HIGH",
        total_orders=1842,
        late_orders=421,
        late_rate=22.8,
        avg_delay_days=5.4,
        associated_products=["P00001", "P00003"],
    )

    assert chunk.chunk_id == "supplier_SUP001_risk"
    assert chunk.document_type == "supplier_risk_profile"
    assert chunk.entity_type == "supplier"
    assert chunk.entity_id == "SUP001"
    assert chunk.risk_level == "HIGH"
    assert "Overall Risk Score: 72.4" in chunk.content
    assert "Late Rate: 22.8%" in chunk.content
    assert chunk.metadata["supplier_id"] == "SUP001"
    assert "P00003" in chunk.metadata["associated_products"]


def test_2_inventory_product_chunking():
    chunk = BusinessChunkingService.create_inventory_chunk(
        product_id="P00003",
        product_name="Critical Industrial Bearing",
        category="Industrial",
        risk_score=89.03,
        risk_level="CRITICAL",
        avg_inventory=4.2,
        avg_daily_demand=22.29,
        days_of_cover=0.19,
        stockout_rate=87.83,
        demand_pressure=84.14,
        supplier_ids=["S0043"],
    )

    assert chunk.chunk_id == "product_P00003_inventory"
    assert chunk.document_type == "inventory_risk_profile"
    assert chunk.entity_type == "product"
    assert chunk.entity_id == "P00003"
    assert chunk.risk_level == "CRITICAL"
    assert "Stockout Rate: 87.82%" in chunk.content or "87.83%" in chunk.content
    assert "Days of Cover: 0.19" in chunk.content
    assert chunk.metadata["product_id"] == "P00003"


def test_3_route_and_disruption_chunking():
    route_chunk = BusinessChunkingService.create_route_chunk(
        route_id="R001",
        origin="Hyderabad",
        destination="Mumbai",
        risk_score=30.06,
        risk_level="MEDIUM",
        avg_delay_days=1.5,
        disruption_count=2,
    )
    assert route_chunk.chunk_id == "route_R001_risk"
    assert route_chunk.document_type == "route_risk_profile"
    assert route_chunk.entity_id == "R001"
    assert "Hyderabad" in route_chunk.content

    disrupt_chunk = BusinessChunkingService.create_disruption_chunk(
        disruption_id="D001",
        route_id="R001",
        event_type="Port Congestion",
        severity="HIGH",
        description="Significant customs clearance backlog delaying transit.",
        impact_duration_days=4,
    )
    assert disrupt_chunk.chunk_id == "disruption_D001"
    assert disrupt_chunk.document_type == "disruption_profile"
    assert disrupt_chunk.risk_level == "HIGH"


# =====================================================================
# 2. EMBEDDING PROVIDER TESTS
# =====================================================================
def test_4_embedding_provider_abstraction():
    provider = get_embedding_provider()
    assert isinstance(provider, EmbeddingProvider)

    texts = [
        "Supplier SUP001 has high delivery delay risk.",
        "Product P00003 has critical stockout exposure.",
    ]
    doc_vectors = provider.embed_documents(texts)
    assert len(doc_vectors) == 2
    assert len(doc_vectors[0]) == provider.dimension

    # Deterministic query embedding
    q_vec1 = provider.embed_query("Supplier delivery risk")
    q_vec2 = provider.embed_query("Supplier delivery risk")
    assert len(q_vec1) == provider.dimension
    assert q_vec1 == q_vec2


# =====================================================================
# 3. VECTOR STORE & RBAC SEARCH TESTS
# =====================================================================
def test_5_vector_store_indexing_and_search(tmp_path):
    store_file = tmp_path / "test_store.joblib"
    store = LocalVectorStore(store_path=store_file)

    chunks = [
        BusinessChunkingService.create_supplier_chunk(
            supplier_id="SUP001",
            risk_score=75.0,
            risk_level="HIGH",
            total_orders=100,
            late_orders=30,
            late_rate=30.0,
            avg_delay_days=6.0,
        ),
        BusinessChunkingService.create_supplier_chunk(
            supplier_id="SUP002",
            risk_score=15.0,
            risk_level="LOW",
            total_orders=200,
            late_orders=2,
            late_rate=1.0,
            avg_delay_days=0.5,
        ),
        BusinessChunkingService.create_inventory_chunk(
            product_id="P00003",
            risk_score=90.0,
            risk_level="CRITICAL",
            avg_inventory=2.0,
            avg_daily_demand=20.0,
            days_of_cover=0.1,
            stockout_rate=90.0,
            demand_pressure=85.0,
        ),
    ]

    stats = store.build_index(chunks)
    assert stats.total_chunks == 3
    assert stats.is_indexed is True

    # Persistence verification
    store2 = LocalVectorStore(store_path=store_file)
    assert len(store2.chunks) == 3

    # Search entity lookup
    results = store2.search("Why is P00003 at risk?", top_k=2)
    assert len(results) > 0
    assert results[0][0].entity_id == "P00003"
    assert results[0][1] >= 0.5


def test_6_vector_store_supplier_rbac_isolation(tmp_path):
    store_file = tmp_path / "rbac_store.joblib"
    store = LocalVectorStore(store_path=store_file)

    chunks = [
        BusinessChunkingService.create_supplier_chunk(
            supplier_id="S0001",
            risk_score=75.0,
            risk_level="HIGH",
            total_orders=100,
            late_orders=20,
            late_rate=20.0,
            avg_delay_days=4.0,
        ),
        BusinessChunkingService.create_supplier_chunk(
            supplier_id="S0002",
            risk_score=80.0,
            risk_level="HIGH",
            total_orders=100,
            late_orders=25,
            late_rate=25.0,
            avg_delay_days=5.0,
        ),
    ]
    store.build_index(chunks)

    supplier_1_scope = QueryScope(
        username="supplier1",
        role="SUPPLIER",
        supplier_id="S0001",
    )

    # Supplier 1 searches: should ONLY see S0001 chunks
    results = store.search(
        query="Show high risk suppliers",
        top_k=5,
        user_scope=supplier_1_scope,
    )
    for c, score in results:
        assert c.entity_id == "S0001"
        assert c.entity_id != "S0002"


# =====================================================================
# 4. HYBRID RETRIEVAL TESTS
# =====================================================================
def test_7_hybrid_retrieval_combination():
    hybrid_retriever = HybridRetriever(alpha=0.5, beta=0.5)

    res = hybrid_retriever.retrieve(
        query="Why is product P00003 at inventory risk?",
        top_k=3,
        include_semantic=True,
    )
    assert res.retrieval_mode in ["hybrid", "semantic", "structured"]
    assert isinstance(res.combined_evidence, list)
    assert res.latency_ms > 0

    if res.combined_evidence:
        top_item = res.combined_evidence[0]
        assert "combined_score" in top_item
        assert "provenance" in top_item


# =====================================================================
# 5. END-TO-END QUERY SERVICE INTEGRATION
# =====================================================================
def test_8_query_service_hybrid_integration():
    qs = QueryService()

    # 1. Contextual / Explanatory Query
    res_context = qs.query("Why is product P00003 at inventory risk?")
    assert res_context["status"] == "success"
    assert res_context["fallback_used"] is False
    assert len(res_context["evidence"]) > 0

    # 2. Unsupported / Out-of-Domain Query -> Controlled Fallback
    res_ood = qs.query("What is the weather in Tokyo?")
    assert res_ood["fallback_used"] is True
    assert res_ood["status"] in ["clarification", "fallback"]


# =====================================================================
# 6. RETRIEVAL EVALUATION METRICS
# =====================================================================
def test_9_retrieval_evaluation_metrics():
    eval_result = RetrievalEvaluator.evaluate_retrieval(
        query="Why is product P00003 at inventory risk?",
        expected_entities=["P00003"],
        retrieved_evidence=[
            {
                "entity_id": "P00003",
                "chunk_id": "product_P00003_inventory",
                "score": 0.92,
                "confidence": 0.92,
                "value": "Days of Cover: 0.19 days, Stockout Rate: 87.8%",
            }
        ],
        response_text="Product P00003 has critical stockout rate of 87.8%.",
        semantic_latency_ms=12.5,
        total_latency_ms=25.0,
    )

    assert eval_result["retrieval_hit"] is True
    assert eval_result["retrieval_hit_rate"] == 1.0
    assert eval_result["retrieval_relevance"] >= 0.90
    assert eval_result["grounding_score"] == 1.0
    assert eval_result["semantic_retrieval_latency_ms"] == 12.5

    # Summary metrics computation
    summary = RetrievalEvaluator.compute_summary([eval_result])
    assert summary["total_retrieval_evaluations"] == 1
    assert summary["retrieval_hit_rate"] == 1.0
    assert summary["average_grounding_score"] == 1.0
