from __future__ import annotations

import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.models.entities import User, UserRole
from app.services.auth_service import get_current_user_optional, require_roles
from app.query.scope import QueryScope
from app.services.retrieval.document_builder import KnowledgeDocumentBuilder
from app.services.retrieval.retrieval_models import RetrievalStats
from app.services.retrieval.semantic_retriever import SemanticRetriever
from app.services.retrieval.vector_store import LocalVectorStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/retrieval", tags=["Retrieval & Vector Store"])

# Shared singleton vector store
_vector_store: LocalVectorStore | None = None


def get_vector_store() -> LocalVectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = LocalVectorStore()
    return _vector_store


class RetrievalSearchRequest(BaseModel):
    query: str = Field(..., description="Natural language search query")
    top_k: int = Field(5, ge=1, le=25, description="Number of chunks to retrieve")
    document_type: str | None = Field(None, description="Filter by document type")
    entity_type: str | None = Field(None, description="Filter by entity type (supplier, product, route)")
    target_entity_id: str | None = Field(None, description="Target entity ID filter")
    risk_level: str | None = Field(None, description="Risk level filter (CRITICAL, HIGH, MEDIUM, LOW)")


class RetrievalSearchResponse(BaseModel):
    status: str = "success"
    query: str
    total_results: int
    results: list[dict[str, Any]]


@router.post("/index", summary="Re-index Knowledge Chunks into Vector Store")
def trigger_indexing(
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> dict[str, Any]:
    """
    Administrative endpoint to extract operational telemetry and
    re-index business-level chunks into the persistent local vector store.
    """
    try:
        builder = KnowledgeDocumentBuilder()
        chunks = builder.build_all_chunks()
        store = get_vector_store()
        stats = store.build_index(chunks)
        return {
            "status": "success",
            "message": f"Successfully indexed {stats.total_chunks} business-level knowledge chunks.",
            "stats": stats.to_dict(),
        }
    except Exception as e:
        logger.error(f"Error during manual indexing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Indexing failed: {str(e)}",
        )


@router.get("/stats", summary="Get Vector Store Indexing Statistics")
def get_retrieval_stats() -> dict[str, Any]:
    """
    Returns telemetry and telemetry on the persistent semantic vector store.
    """
    store = get_vector_store()
    stats = store.get_stats()
    return {
        "status": "success",
        "stats": stats.to_dict(),
    }


@router.post("/search", response_model=RetrievalSearchResponse, summary="Semantic Vector Search")
def search_vector_store(
    payload: RetrievalSearchRequest,
    current_user: User | None = Depends(get_current_user_optional),
) -> RetrievalSearchResponse:
    """
    Executes semantic vector search across business-level chunks with RBAC isolation.
    """
    user_scope = QueryScope.from_user(current_user) if current_user else None
    store = get_vector_store()
    retriever = SemanticRetriever(vector_store=store)

    res = retriever.retrieve(
        query=payload.query,
        top_k=payload.top_k,
        user_scope=user_scope,
        document_type=payload.document_type,
        entity_type=payload.entity_type,
        target_entity_id=payload.target_entity_id,
        risk_level=payload.risk_level,
    )

    formatted_results = [
        {
            "chunk_id": item.get("chunk_id"),
            "entity_id": item.get("entity_id"),
            "document_type": item.get("document_type"),
            "score": item.get("score"),
            "content": item.get("value"),
            "source_type": "semantic",
            "metadata": item.get("metadata", {}),
        }
        for item in res.evidence
    ]

    return RetrievalSearchResponse(
        status="success",
        query=payload.query,
        total_results=len(formatted_results),
        results=formatted_results,
    )
