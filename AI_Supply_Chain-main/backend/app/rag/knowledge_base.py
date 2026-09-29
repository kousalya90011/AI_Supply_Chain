from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.query.scope import QueryScope, supplier_ids_match
from app.rag.schemas import KnowledgeDocument

logger = logging.getLogger(__name__)

DEFAULT_STORE_PATH = Path(__file__).resolve().parents[2] / "data" / "knowledge_base" / "vector_store.joblib"


class LocalVectorStore:
    """
    Local, persistent, RBAC-aware semantic vector index using scikit-learn
    TF-IDF vectors and cosine similarity.

    Zero external infrastructure, runs reliably on Windows without C++ build dependencies,
    and guarantees strict pre-filtering for supplier scopes.
    """

    def __init__(self, store_path: Path | str | None = None) -> None:
        self.store_path = Path(store_path or DEFAULT_STORE_PATH)
        self.vectorizer = TfidfVectorizer(
            max_features=15000,
            ngram_range=(1, 2),
            sublinear_tf=True,
            stop_words="english",
        )
        self.documents: list[KnowledgeDocument] = []
        self.doc_matrix: Any = None
        self.is_indexed: bool = False

    def build_index(self, documents: list[KnowledgeDocument]) -> None:
        """
        Builds the vector space model from a list of knowledge documents.
        """
        if not documents:
            logger.warning("No documents provided to build vector index.")
            self.documents = []
            self.doc_matrix = None
            self.is_indexed = False
            return

        self.documents = documents

        # Build corpus by combining title, entity_id, keywords, and content
        corpus = [
            f"{doc.title} {doc.entity_id} {' '.join(doc.metadata.get('supplier_ids', []))} {doc.content}"
            for doc in documents
        ]

        self.doc_matrix = self.vectorizer.fit_transform(corpus)
        self.is_indexed = True
        logger.info(f"Built vector index with {len(self.documents)} documents.")

    def persist(self, path: Path | str | None = None) -> Path:
        """
        Persists the index, vectorizer, and documents to disk.
        """
        save_path = Path(path or self.store_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "documents": [doc.to_dict() for doc in self.documents],
            "vectorizer": self.vectorizer,
            "doc_matrix": self.doc_matrix,
            "is_indexed": self.is_indexed,
        }

        joblib.dump(payload, save_path, compress=3)
        logger.info(f"Persisted vector store to {save_path}")
        return save_path

    def load(self, path: Path | str | None = None) -> bool:
        """
        Loads the index from disk if available.
        """
        target_path = Path(path or self.store_path)
        if not target_path.exists():
            return False

        try:
            payload = joblib.load(target_path)
            raw_docs = payload.get("documents") or payload.get("chunks") or []
            self.documents = [
                KnowledgeDocument(
                    doc_id=d.get("doc_id") or d.get("chunk_id", ""),
                    doc_type=d.get("doc_type") or d.get("entity_type", "knowledge"),
                    entity_id=d.get("entity_id", ""),
                    title=d.get("title", ""),
                    content=d.get("content", ""),
                    metadata=d.get("metadata", {}),
                )
                for d in raw_docs
            ]
            self.vectorizer = payload.get("vectorizer", self.vectorizer)
            self.doc_matrix = payload.get("doc_matrix") if payload.get("doc_matrix") is not None else payload.get("chunk_matrix")
            self.is_indexed = payload.get("is_indexed", bool(self.documents))
            logger.info(f"Loaded vector store with {len(self.documents)} documents from {target_path}")
            return True
        except Exception as e:
            logger.warning(f"Failed to load vector store from {target_path}: {e}")
            return False

    def search(
        self,
        query: str,
        top_k: int = 5,
        user_scope: QueryScope | None = None,
        doc_type: str | None = None,
        target_entity_id: str | None = None,
        topic: str | None = None,
        risk_level: str | None = None,
    ) -> list[tuple[KnowledgeDocument, float]]:
        """
        Searches the vector store with strict RBAC pre-filtering.

        Defense in depth:
        - For SUPPLIER users: evaluates ONLY documents authorized for that supplier.
        - Documents for other suppliers are strictly excluded prior to similarity scoring.
        """
        if not self.is_indexed or not self.documents or self.doc_matrix is None:
            return []

        cleaned_query = (query or "").strip()
        if not cleaned_query:
            return []

        # -----------------------------------------------------
        # 1. RBAC PRE-FILTERING (Crucial Requirement 12)
        # -----------------------------------------------------
        candidate_indices: list[int] = []

        is_supplier = bool(user_scope and getattr(user_scope, "is_supplier", False))
        user_sid = getattr(user_scope, "supplier_id", None) if is_supplier else None

        for idx, doc in enumerate(self.documents):
            # Enforce supplier scope
            if is_supplier and user_sid:
                doc_sids = doc.metadata.get("supplier_ids", [])
                # If document is not associated with this supplier, exclude completely
                if not any(supplier_ids_match(user_sid, sid) for sid in doc_sids):
                    continue

            # Optional doc_type filter
            if doc_type and doc.doc_type != doc_type:
                continue

            # Optional topic filter
            if topic and doc.metadata.get("topic") != topic:
                continue

            # Optional risk_level filter
            if risk_level and doc.metadata.get("risk_level") != risk_level:
                continue

            # Optional target_entity_id filter
            if target_entity_id:
                target_str = str(target_entity_id).upper()
                entity_matches = (
                    str(doc.entity_id).upper() == target_str
                    or supplier_ids_match(doc.entity_id, target_str)
                )
                if not entity_matches:
                    pids = [str(p).upper() for p in doc.metadata.get("product_ids", [])]
                    sids = [str(s).upper() for s in doc.metadata.get("supplier_ids", [])]
                    supplier_in_meta = any(supplier_ids_match(s, target_str) for s in sids)
                    if target_str not in pids and not supplier_in_meta:
                        continue

            candidate_indices.append(idx)

        if not candidate_indices:
            return []

        # -----------------------------------------------------
        # 2. VECTOR SIMILARITY COMPUTATION
        # -----------------------------------------------------
        try:
            query_vec = self.vectorizer.transform([cleaned_query])
            sub_matrix = self.doc_matrix[candidate_indices]
            sims = cosine_similarity(query_vec, sub_matrix)[0]

            scored_candidates: list[tuple[KnowledgeDocument, float]] = []
            for sub_idx, score in enumerate(sims):
                orig_idx = candidate_indices[sub_idx]
                doc = self.documents[orig_idx]

                # Boost exact entity identifier matches in query
                final_score = float(score)
                if doc.entity_id.upper() in cleaned_query.upper():
                    final_score = max(final_score + 0.35, 0.95)

                scored_candidates.append((doc, round(final_score, 4)))

            scored_candidates.sort(key=lambda x: x[1], reverse=True)
            return scored_candidates[:top_k]

        except Exception as e:
            logger.warning(f"Error during vector search: {e}")
            return []
