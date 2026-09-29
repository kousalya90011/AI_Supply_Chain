from __future__ import annotations

from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any
import joblib
import numpy as np

from app.config import settings
from app.query.scope import QueryScope, supplier_ids_match
from app.services.retrieval.embeddings import EmbeddingProvider, get_embedding_provider
from app.services.retrieval.retrieval_models import BusinessChunk, RetrievalStats

logger = logging.getLogger(__name__)

DEFAULT_STORE_DIR = Path(__file__).resolve().parents[3] / "data" / "knowledge_base"
DEFAULT_STORE_FILE = DEFAULT_STORE_DIR / "vector_store.joblib"


class LocalVectorStore:
    """
    Lightweight, persistent local vector store supporting cosine similarity search,
    strict RBAC pre-filtering, and metadata indexing.

    Zero external infrastructure required, fully runnable on Windows/Python 3.13.
    """

    def __init__(
        self,
        store_path: Path | str | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.store_path = Path(store_path or DEFAULT_STORE_FILE)
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self.chunks: list[BusinessChunk] = []
        self.chunk_matrix: np.ndarray | None = None
        self.is_indexed: bool = False
        self.last_indexed_at: str | None = None

        # Auto-load existing persisted store if available
        if self.store_path.exists():
            self.load()

    def build_index(self, chunks: list[BusinessChunk]) -> RetrievalStats:
        """
        Builds the vector store index from business-level chunks.
        Embeds chunk texts and persists the index.
        """
        if not chunks:
            logger.warning("No chunks provided to build vector index.")
            self.chunks = []
            self.chunk_matrix = None
            self.is_indexed = False
            return self.get_stats()

        self.chunks = chunks

        # Prepare corpus text combining title, entity ID, metadata keywords, and content
        corpus = [
            f"{c.title} {c.entity_id} {' '.join(str(v) for v in c.metadata.values() if isinstance(v, (str, int)))} {c.content}"
            for c in chunks
        ]

        logger.info(f"Generating embeddings for {len(corpus)} chunks using {self.embedding_provider.provider_name}...")
        embeddings = self.embedding_provider.embed_documents(corpus)
        self.chunk_matrix = np.array(embeddings, dtype=np.float32)

        # Attach embedding vectors to chunks for completeness
        for idx, c in enumerate(self.chunks):
            c.embedding = embeddings[idx]

        self.is_indexed = True
        self.last_indexed_at = datetime.now(timezone.utc).isoformat()
        self.persist()

        stats = self.get_stats()
        logger.info(f"Successfully built and persisted vector index: {stats.total_chunks} chunks.")
        return stats

    def persist(self, path: Path | str | None = None) -> Path:
        """Persists chunks, embeddings, and provider state to disk."""
        target_path = Path(path or self.store_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        legacy_docs = []
        for c in self.chunks:
            d = c.to_dict()
            d["doc_id"] = c.chunk_id
            d["doc_type"] = c.entity_type
            legacy_docs.append(d)

        payload = {
            "chunks": [c.to_dict() for c in self.chunks],
            "documents": legacy_docs,
            "raw_chunks": self.chunks,
            "chunk_matrix": self.chunk_matrix,
            "doc_matrix": self.chunk_matrix,
            "vectorizer": getattr(self.embedding_provider, "_vectorizer", None),
            "provider_name": self.embedding_provider.provider_name,
            "provider_state": getattr(self.embedding_provider, "get_state", lambda: {})(),
            "last_indexed_at": self.last_indexed_at,
            "is_indexed": self.is_indexed,
        }

        joblib.dump(payload, target_path, compress=3)
        logger.info(f"Vector store persisted to {target_path}")
        return target_path

    def load(self, path: Path | str | None = None) -> bool:
        """Loads index from disk."""
        target_path = Path(path or self.store_path)
        if not target_path.exists():
            return False

        try:
            payload = joblib.load(target_path)
            raw = payload.get("raw_chunks")
            if raw and isinstance(raw, list):
                self.chunks = raw
            else:
                self.chunks = [
                    BusinessChunk(**d) for d in payload.get("chunks", [])
                ]

            self.chunk_matrix = payload.get("chunk_matrix")
            self.last_indexed_at = payload.get("last_indexed_at")
            self.is_indexed = payload.get("is_indexed", bool(self.chunks))

            state = payload.get("provider_state")
            if state and hasattr(self.embedding_provider, "set_state"):
                self.embedding_provider.set_state(state)

            logger.info(f"Loaded vector store with {len(self.chunks)} chunks from {target_path}")
            return True
        except Exception as e:
            logger.warning(f"Failed to load vector store from {target_path}: {e}")
            return False

    def search(
        self,
        query: str,
        top_k: int = 5,
        user_scope: QueryScope | None = None,
        document_type: str | None = None,
        entity_type: str | None = None,
        target_entity_id: str | None = None,
        risk_level: str | None = None,
    ) -> list[tuple[BusinessChunk, float]]:
        """
        Executes semantic vector search with strict RBAC pre-filtering.

        Pre-filtering guarantees:
        - Supplier users can ONLY retrieve chunks associated with their own supplier ID.
        - Other suppliers' chunks are eliminated BEFORE vector similarity evaluation.
        """
        if not self.is_indexed or not self.chunks or self.chunk_matrix is None:
            return []

        cleaned_query = (query or "").strip()
        if not cleaned_query:
            return []

        # -----------------------------------------------------
        # 1. RBAC & METADATA PRE-FILTERING
        # -----------------------------------------------------
        is_supplier = bool(user_scope and getattr(user_scope, "is_supplier", False))
        user_sid = getattr(user_scope, "supplier_id", None) if is_supplier else None

        candidate_indices: list[int] = []
        for idx, chunk in enumerate(self.chunks):
            # Strict supplier RBAC boundary
            if is_supplier and user_sid:
                chunk_sid = chunk.metadata.get("supplier_id") or (
                    chunk.entity_id if chunk.entity_type == "supplier" else None
                )
                chunk_sids = chunk.metadata.get("supplier_ids", [])
                matches_supplier = (
                    supplier_ids_match(user_sid, chunk_sid)
                    or any(supplier_ids_match(user_sid, s) for s in chunk_sids)
                )
                # Allow general knowledge methodology chunks to be read by all roles
                is_general_knowledge = chunk.entity_type == "knowledge"
                if not (matches_supplier or is_general_knowledge):
                    continue

            # Optional document_type filter
            if document_type and chunk.document_type != document_type:
                continue

            # Optional entity_type filter
            if entity_type and chunk.entity_type != entity_type:
                continue

            # Optional risk_level filter
            if risk_level and chunk.risk_level != risk_level.upper():
                continue

            # Optional target_entity_id filter
            if target_entity_id:
                t_str = str(target_entity_id).upper()
                entity_matches = (
                    chunk.entity_id.upper() == t_str
                    or supplier_ids_match(chunk.entity_id, t_str)
                    or t_str in [str(s).upper() for s in chunk.metadata.get("supplier_ids", [])]
                    or t_str in [str(p).upper() for p in chunk.metadata.get("associated_products", [])]
                )
                if not entity_matches:
                    continue

            candidate_indices.append(idx)

        if not candidate_indices:
            return []

        # -----------------------------------------------------
        # 2. VECTOR SIMILARITY COMPUTATION
        # -----------------------------------------------------
        try:
            query_vec = np.array(self.embedding_provider.embed_query(cleaned_query), dtype=np.float32)
            # Normalize query vector for cosine similarity
            q_norm = np.linalg.norm(query_vec)
            if q_norm > 0:
                query_vec = query_vec / q_norm

            sub_matrix = self.chunk_matrix[candidate_indices]
            # Compute dot product (cosine similarity since vectors are normalized)
            norms = np.linalg.norm(sub_matrix, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            normed_sub = sub_matrix / norms
            sims = np.dot(normed_sub, query_vec)

            scored: list[tuple[BusinessChunk, float]] = []
            upper_query = cleaned_query.upper()

            for sub_idx, score in enumerate(sims):
                orig_idx = candidate_indices[sub_idx]
                chunk = self.chunks[orig_idx]
                final_score = float(score)

                # Entity identifier boost: if exact entity ID is in the query, reward it
                if chunk.entity_id and chunk.entity_id.upper() in upper_query:
                    final_score = max(final_score + 0.30, 0.92)

                scored.append((chunk, round(final_score, 4)))

            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:top_k]

        except Exception as e:
            logger.warning(f"Error during vector search: {e}")
            return []

    def get_stats(self) -> RetrievalStats:
        """Returns statistics on stored knowledge chunks."""
        by_type: dict[str, int] = {}
        by_risk: dict[str, int] = {}

        for c in self.chunks:
            by_type[c.document_type] = by_type.get(c.document_type, 0) + 1
            if c.risk_level:
                by_risk[c.risk_level] = by_risk.get(c.risk_level, 0) + 1

        return RetrievalStats(
            total_chunks=len(self.chunks),
            chunks_by_type=by_type,
            chunks_by_risk=by_risk,
            embedding_provider=self.embedding_provider.provider_name,
            vector_store_type="local_vector_store",
            store_path=str(self.store_path),
            last_indexed_at=self.last_indexed_at,
            is_indexed=self.is_indexed,
        )
