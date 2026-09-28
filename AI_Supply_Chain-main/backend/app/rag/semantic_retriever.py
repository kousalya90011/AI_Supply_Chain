from __future__ import annotations

import logging
from typing import Any
from pathlib import Path

from app.query.scope import QueryScope
from app.rag.knowledge_base import LocalVectorStore, DEFAULT_STORE_PATH
from app.rag.schemas import EvidenceItem, KnowledgeDocument, RetrievalResult

logger = logging.getLogger(__name__)


class SemanticRetriever:
    """
    Performs semantic vector search across product and supplier knowledge documents
    with strict RBAC pre-filtering.
    """

    def __init__(self, vector_store: LocalVectorStore | None = None) -> None:
        self.vector_store = vector_store or LocalVectorStore()
        if not self.vector_store.is_indexed:
            # Try to load existing persisted index
            self.vector_store.load()

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        user_scope: QueryScope | None = None,
        doc_type: str | None = None,
        target_entity_id: str | None = None,
        topic: str | None = None,
        risk_level: str | None = None,
    ) -> RetrievalResult:
        """
        Retrieves matching knowledge documents and converts them to standard EvidenceItems.
        """
        # Search the vector store with RBAC and metadata pre-filtering
        matches = self.vector_store.search(
            query=query,
            top_k=top_k,
            user_scope=user_scope,
            doc_type=doc_type,
            target_entity_id=target_entity_id,
            topic=topic,
            risk_level=risk_level,
        )

        evidence_items: list[dict[str, Any]] = []
        documents: list[KnowledgeDocument] = []
        sources: set[str] = set()

        for doc, score in matches:
            documents.append(doc)
            sources.add(f"Knowledge Base ({doc.doc_type.capitalize()}: {doc.entity_id})")

            topic_label = str(doc.metadata.get("topic", "operational_profile")).replace("_", " ").title()
            ev = EvidenceItem(
                source_type="knowledge_base",
                source_id=doc.doc_id,
                entity_type=doc.doc_type,
                entity_id=doc.entity_id,
                metric=doc.metadata.get("topic", "knowledge_summary"),
                value=doc.content,
                explanation=f"{doc.title}: {doc.content}",
                retrieval_method="semantic",
                confidence=round(score, 4),
            )
            item_dict = ev.to_dict()
            item_dict["topic"] = doc.metadata.get("topic")
            item_dict["metadata"] = doc.metadata
            evidence_items.append(item_dict)

        return RetrievalResult(
            retrieval_mode="semantic",
            evidence=evidence_items,
            documents=documents,
            sources=sorted(sources),
        )
