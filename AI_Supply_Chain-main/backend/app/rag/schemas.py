from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass
class EvidenceItem:
    """
    Standard evidence representation as required by Phase 5 Requirement 13.
    """
    source_type: str  # "analytics", "database", "knowledge_base", "hybrid"
    entity_type: str  # "product", "supplier", "order", "inventory", etc.
    entity_id: str | None = None
    source_id: str | None = None
    metric: str | None = None
    value: Any = None
    explanation: str | None = None
    retrieval_method: Literal["structured", "semantic"] = "structured"
    confidence: float | None = 1.0

    data: Any = None
    source: str | None = None
    entity: str | None = None

    def to_dict(self) -> dict[str, Any]:
        source_id = self.source_id or f"{self.entity_type}:{self.entity_id}"
        # Build standard data dict for backward compatibility
        item_data = self.data
        if item_data is None:
            item_data = {
                "metric": self.metric,
                "value": self.value,
                "entity_type": self.entity_type,
                "entity_id": self.entity_id,
            }
            if self.entity_type == "supplier" and self.entity_id:
                item_data["supplier_id"] = self.entity_id
            elif self.entity_type == "product" and self.entity_id:
                item_data["product_id"] = self.entity_id
            if isinstance(self.value, dict):
                item_data.update(self.value)

        return {
            # Phase 5 standard fields (Requirement 13)
            "source_type": self.source_type,
            "source_id": source_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "metric": self.metric,
            "value": self.value,
            "explanation": self.explanation,
            "retrieval_method": self.retrieval_method,
            "confidence": self.confidence,
            # Backward-compatible fields
            "source": self.source or self.metric or self.source_type,
            "entity": self.entity or self.entity_type,
            "data": item_data,
        }


@dataclass
class KnowledgeDocument:
    """
    Represents an aggregated semantic document for an entity (Product or Supplier).
    """
    doc_id: str  # e.g., "product:P00003", "supplier:S001"
    doc_type: Literal["product", "supplier"]
    entity_id: str
    title: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "doc_type": self.doc_type,
            "entity_id": self.entity_id,
            "title": self.title,
            "content": self.content,
            "metadata": self.metadata,
        }


@dataclass
class RetrievalResult:
    """
    Encapsulates the output of structured, semantic, or hybrid retrieval.
    """
    retrieval_mode: Literal["structured", "semantic", "hybrid"]
    evidence: list[dict[str, Any]] = field(default_factory=list)
    documents: list[KnowledgeDocument] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    summary: str | None = None
