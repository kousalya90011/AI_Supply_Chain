from __future__ import annotations

import logging
from typing import Any
from app.config import settings
from app.query.scope import QueryScope, supplier_ids_match
from app.rag.schemas import KnowledgeDocument
from app.guardrails.schemas import GuardrailResult

logger = logging.getLogger(__name__)


class RAGRetrievalGuardrail:
    """
    Guards retrieval operations across the hybrid RAG architecture.

    Enforces:
    - Pre- and post-retrieval RBAC boundary verification.
    - Result deduplication.
    - Strict Top-K bounding (MAX_TOP_K).
    - Configurable minimum similarity score thresholding.
    - Evidence item bounding (MAX_EVIDENCE_ITEMS).
    - Detection of insufficient evidence states.
    - Treating retrieved documents as untrusted data rather than executable instructions.
    """

    def __init__(
        self,
        max_top_k: int | None = None,
        max_evidence: int | None = None,
        min_score: float | None = None,
    ) -> None:
        self.max_top_k = max_top_k or getattr(settings, "MAX_TOP_K", 5)
        self.max_evidence = max_evidence or getattr(settings, "MAX_EVIDENCE_ITEMS", 15)
        self.min_score = min_score if min_score is not None else getattr(settings, "MIN_RETRIEVAL_SCORE", 0.05)

    def bound_top_k(self, requested_top_k: int) -> int:
        """Enforces upper bound on requested top_k."""
        return max(1, min(requested_top_k, self.max_top_k))

    def validate_and_filter_documents(
        self,
        scored_docs: list[tuple[KnowledgeDocument, float]],
        user_scope: QueryScope | None = None,
    ) -> list[tuple[KnowledgeDocument, float]]:
        """
        Applies post-retrieval RBAC validation, score thresholding, and deduplication.
        """
        is_supplier = bool(user_scope and getattr(user_scope, "is_supplier", False))
        user_sid = getattr(user_scope, "supplier_id", None) if is_supplier else None

        seen_doc_ids: set[str] = set()
        validated: list[tuple[KnowledgeDocument, float]] = []

        for doc, score in scored_docs:
            # 1. Similarity threshold check
            if score < self.min_score:
                continue

            # 2. Strict Supplier Scope Boundary Check (Zero cross-supplier leakage)
            if is_supplier and user_sid:
                doc_sids = doc.metadata.get("supplier_ids", [])
                doc_entity = str(doc.entity_id)
                # Match either entity ID or metadata supplier list
                is_authorized = supplier_ids_match(doc_entity, user_sid) or any(
                    supplier_ids_match(user_sid, sid) for sid in doc_sids
                )
                if not is_authorized:
                    logger.warning(
                        f"RAGGuardrail: Blocked unauthorized document {doc.doc_id} (entity={doc_entity}) for user {user_scope.username}"
                    )
                    continue

            # 3. Deduplication by doc_id
            if doc.doc_id in seen_doc_ids:
                continue

            seen_doc_ids.add(doc.doc_id)
            validated.append((doc, score))

            if len(validated) >= self.max_top_k:
                break

        return validated

    def bound_evidence(self, evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Caps the maximum evidence items sent downstream to the LLM or synthesis layer."""
        if not evidence:
            return []
        return evidence[: self.max_evidence]

    def verify_evidence_sufficiency(
        self,
        evidence: list[dict[str, Any]],
        requires_evidence: bool = True,
    ) -> GuardrailResult:
        """Determines if the retrieved evidence is adequate to answer factual claims."""
        if requires_evidence and len(evidence) == 0:
            return GuardrailResult(
                passed=False,
                guardrail_name="RAGRetrievalGuardrail",
                action="fallback",
                reason="insufficient_evidence",
                user_message="Insufficient supply-chain evidence was found to answer this inquiry with verified operational facts.",
                metadata={"evidence_count": 0},
            )

        return GuardrailResult(
            passed=True,
            guardrail_name="RAGRetrievalGuardrail",
            action="allow",
            metadata={"evidence_count": len(evidence)},
        )
