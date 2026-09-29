from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


@dataclass
class BusinessChunk:
    """
    Represents a discrete, business-level semantic knowledge chunk
    with structured metadata and provenance traceability.
    """
    chunk_id: str
    document_type: str
    entity_type: str
    entity_id: str
    title: str
    content: str
    source: str
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    risk_level: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Exclude raw embedding vector from standard dict serialization if desired
        if d.get("embedding") is not None:
            d["has_embedding"] = True
            del d["embedding"]
        return d


@dataclass
class SemanticEvidenceItem:
    """
    Standardized semantic evidence representation for hybrid retrieval.
    """
    source_type: Literal["semantic"] = "semantic"
    document_type: str = ""
    entity_type: str = ""
    entity_id: str = ""
    chunk_id: str = ""
    content: str = ""
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "document_type": self.document_type,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "chunk_id": self.chunk_id,
            "content": self.content,
            "score": round(self.score, 4),
            "confidence": round(self.score, 4),
            "metric": self.document_type,
            "value": self.content,
            "explanation": f"[{self.chunk_id}] {self.content[:150]}...",
            "retrieval_method": "semantic",
            "metadata": self.metadata,
        }


@dataclass
class HybridEvidence:
    """
    Unified container combining structured analytical facts and semantic contextual evidence.
    """
    query: str
    structured_evidence: list[dict[str, Any]] = field(default_factory=list)
    semantic_evidence: list[dict[str, Any]] = field(default_factory=list)
    combined_evidence: list[dict[str, Any]] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    scoring_weights: dict[str, float] = field(
        default_factory=lambda: {"alpha_structured": 0.5, "beta_semantic": 0.5}
    )
    retrieval_mode: Literal["structured", "semantic", "hybrid"] = "hybrid"
    latency_ms: float = 0.0
    semantic_latency_ms: float = 0.0
    structured_latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RetrievalStats:
    """
    System telemetry and statistics for the semantic vector store.
    """
    total_chunks: int = 0
    chunks_by_type: dict[str, int] = field(default_factory=dict)
    chunks_by_risk: dict[str, int] = field(default_factory=dict)
    embedding_provider: str = "local"
    vector_store_type: str = "local"
    store_path: str = ""
    last_indexed_at: str | None = None
    is_indexed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
