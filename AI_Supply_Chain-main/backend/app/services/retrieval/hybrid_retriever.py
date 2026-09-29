from __future__ import annotations

import logging
import time
from typing import Any
from sqlalchemy.orm import Session

from app.config import settings
from app.query.schema import QueryPlan
from app.query.scope import QueryScope
from app.rag.schemas import RetrievalResult
from app.rag.structured_retriever import StructuredRetriever
from app.services.retrieval.retrieval_models import HybridEvidence
from app.services.retrieval.semantic_retriever import SemanticRetriever

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Coordinates hybrid retrieval combining:
    1. Structured Retrieval: deterministic numerical facts, KPIs, inventory values,
       supplier delay rates, ML demand forecasts.
    2. Semantic Retrieval: chunked business context, risk profiles, disruption telemetry,
       methodology guidelines.

    Applies transparent, configurable composite scoring:
    combined_score = alpha * structured_score + beta * semantic_score
    """

    def __init__(
        self,
        structured_retriever: StructuredRetriever | None = None,
        semantic_retriever: SemanticRetriever | None = None,
        alpha: float | None = None,
        beta: float | None = None,
    ) -> None:
        self.structured_retriever = structured_retriever or StructuredRetriever()
        self.semantic_retriever = semantic_retriever or SemanticRetriever()
        self.alpha = alpha if alpha is not None else getattr(settings, "HYBRID_ALPHA", 0.5)
        self.beta = beta if beta is not None else getattr(settings, "HYBRID_BETA", 0.5)

    def retrieve(
        self,
        query: str,
        plan: QueryPlan | None = None,
        user_scope: QueryScope | None = None,
        top_k: int | None = None,
        db: Session | None = None,
        include_semantic: bool = True,
    ) -> HybridEvidence:
        """
        Executes parallel or sequential structured and semantic retrieval,
        merging results with calibrated scoring and full provenance traceability.
        """
        k = top_k or getattr(settings, "SEMANTIC_TOP_K", 5)
        total_start = time.perf_counter()

        # ---------------------------------------------------------
        # 1. STRUCTURED RETRIEVAL
        # ---------------------------------------------------------
        structured_evidence: list[dict[str, Any]] = []
        structured_sources: list[str] = []
        s_latency_ms = 0.0

        if plan is not None:
            s_start = time.perf_counter()
            try:
                s_res: RetrievalResult = self.structured_retriever.retrieve(
                    plan=plan,
                    user_scope=user_scope,
                    db=db,
                )
                structured_evidence = s_res.evidence
                structured_sources = s_res.sources
            except Exception as e:
                logger.warning(f"Structured retrieval failed: {e}")
            s_latency_ms = round((time.perf_counter() - s_start) * 1000, 2)

        # ---------------------------------------------------------
        # 2. SEMANTIC RETRIEVAL
        # ---------------------------------------------------------
        semantic_evidence: list[dict[str, Any]] = []
        semantic_sources: list[str] = []
        sem_latency_ms = 0.0

        if include_semantic:
            sem_start = time.perf_counter()
            try:
                target_entity = plan.entity_id if plan else None
                entity_type = plan.entity if plan else None

                sem_res = self.semantic_retriever.retrieve(
                    query=query,
                    top_k=k,
                    user_scope=user_scope,
                    target_entity_id=target_entity,
                    entity_type=entity_type,
                )
                semantic_evidence = sem_res.evidence
                semantic_sources = sem_res.sources
            except Exception as e:
                logger.warning(f"Semantic retrieval failed: {e}")
            sem_latency_ms = round((time.perf_counter() - sem_start) * 1000, 2)

        # ---------------------------------------------------------
        # 3. EVIDENCE COMBINATION & WEIGHTED SCORING
        # ---------------------------------------------------------
        combined: list[dict[str, Any]] = []

        # Tag structured evidence (deterministic baseline gets high inherent score)
        for item in structured_evidence:
            item_copy = dict(item)
            item_copy["source_type"] = "structured"
            s_score = float(item_copy.get("confidence", 1.0))
            item_copy["structured_score"] = s_score
            item_copy["semantic_score"] = 0.0
            # Structured calculation weighted score
            item_copy["combined_score"] = round(self.alpha * s_score + self.beta * 0.5, 4)
            item_copy["provenance"] = f"structured_analytics:{item_copy.get('source', 'warehouse')}"
            combined.append(item_copy)

        # Tag semantic evidence
        for item in semantic_evidence:
            item_copy = dict(item)
            item_copy["source_type"] = "semantic"
            sem_score = float(item_copy.get("score", item_copy.get("confidence", 0.5)))
            item_copy["structured_score"] = 0.0
            item_copy["semantic_score"] = sem_score
            item_copy["combined_score"] = round(self.alpha * 0.5 + self.beta * sem_score, 4)
            item_copy["provenance"] = f"vector_store:chunk:{item_copy.get('chunk_id')}"
            combined.append(item_copy)

        # Sort combined evidence by composite score
        combined.sort(key=lambda x: x.get("combined_score", 0.0), reverse=True)

        total_latency_ms = round((time.perf_counter() - total_start) * 1000, 2)
        all_sources = sorted(set(structured_sources + semantic_sources))

        return HybridEvidence(
            query=query,
            structured_evidence=structured_evidence,
            semantic_evidence=semantic_evidence,
            combined_evidence=combined,
            sources=all_sources,
            scoring_weights={"alpha_structured": self.alpha, "beta_semantic": self.beta},
            retrieval_mode="hybrid" if (structured_evidence and semantic_evidence) else (
                "semantic" if semantic_evidence else "structured"
            ),
            latency_ms=total_latency_ms,
            semantic_latency_ms=sem_latency_ms,
            structured_latency_ms=s_latency_ms,
        )
