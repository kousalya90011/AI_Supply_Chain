from __future__ import annotations

import logging
import time
from typing import Any

from app.config import settings
from app.query.scope import QueryScope
from app.rag.schemas import EvidenceItem, RetrievalResult
from app.services.retrieval.retrieval_models import BusinessChunk, SemanticEvidenceItem
from app.services.retrieval.vector_store import LocalVectorStore

logger = logging.getLogger(__name__)


class SemanticRetriever:
    """
    Retrieves semantic business-level chunks from the vector store
    with strict RBAC boundary checks and converts them to standardized evidence items.
    """

    def __init__(self, vector_store: LocalVectorStore | None = None) -> None:
        self.vector_store = vector_store or LocalVectorStore()

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        user_scope: QueryScope | None = None,
        document_type: str | None = None,
        entity_type: str | None = None,
        target_entity_id: str | None = None,
        risk_level: str | None = None,
    ) -> RetrievalResult:
        """
        Executes semantic search and returns standard RetrievalResult with evidence items.
        """
        k = top_k or getattr(settings, "SEMANTIC_TOP_K", 5)
        start_t = time.perf_counter()

        matches = self.vector_store.search(
            query=query,
            top_k=k,
            user_scope=user_scope,
            document_type=document_type,
            entity_type=entity_type,
            target_entity_id=target_entity_id,
            risk_level=risk_level,
        )

        latency_ms = round((time.perf_counter() - start_t) * 1000, 2)

        evidence_items: list[dict[str, Any]] = []
        sources: set[str] = set()

        for chunk, score in matches:
            sources.add(f"Semantic Knowledge ({chunk.document_type}: {chunk.entity_id})")

            # Standard EvidenceItem format matching Phase 5 Requirement 13
            ev = EvidenceItem(
                source_type="semantic",
                source_id=chunk.chunk_id,
                entity_type=chunk.entity_type,
                entity_id=chunk.entity_id,
                metric=chunk.document_type,
                value=chunk.content,
                explanation=f"{chunk.title}: {chunk.content[:200]}...",
                retrieval_method="semantic",
                confidence=round(score, 4),
            )
            item_dict = ev.to_dict()
            item_dict["chunk_id"] = chunk.chunk_id
            item_dict["document_type"] = chunk.document_type
            item_dict["score"] = round(score, 4)
            item_dict["metadata"] = chunk.metadata
            item_dict["retrieval_latency_ms"] = latency_ms
            evidence_items.append(item_dict)

        return RetrievalResult(
            retrieval_mode="semantic",
            evidence=evidence_items,
            sources=sorted(sources),
            summary=f"Retrieved {len(evidence_items)} semantic chunks in {latency_ms:.1f}ms",
        )
