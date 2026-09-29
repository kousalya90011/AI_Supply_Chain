from __future__ import annotations

import re
from typing import Any


class RetrievalEvaluator:
    """
    Evaluates semantic and hybrid retrieval performance:
    - Retrieval hit rate (was the expected entity / chunk retrieved?)
    - Retrieval relevance (relevance of retrieved evidence to query)
    - Evidence grounding (is the answer grounded in retrieved evidence?)
    - Citation / evidence coverage (ratio of evidence utilized in the response)
    - Latency telemetry (semantic vs. hybrid retrieval latency)
    """

    @classmethod
    def evaluate_retrieval(
        cls,
        *,
        query: str,
        expected_entities: list[str] | None = None,
        retrieved_evidence: list[dict[str, Any]],
        response_text: str | None = None,
        semantic_latency_ms: float = 0.0,
        total_latency_ms: float = 0.0,
    ) -> dict[str, Any]:
        """
        Evaluates a single query's retrieval and grounding quality.
        """
        expected_set = {str(e).strip().upper() for e in (expected_entities or [])}

        # 1. Extract retrieved entity IDs and chunk IDs
        retrieved_entities: set[str] = set()
        retrieved_chunks: list[str] = []
        for ev in retrieved_evidence:
            if not isinstance(ev, dict):
                continue
            eid = ev.get("entity_id")
            if eid:
                retrieved_entities.add(str(eid).strip().upper())
            chunk_id = ev.get("chunk_id") or ev.get("source_id")
            if chunk_id:
                retrieved_chunks.append(str(chunk_id))
            data = ev.get("data")
            if isinstance(data, dict):
                for k in ["supplier_id", "product_id"]:
                    val = data.get(k)
                    if val:
                        retrieved_entities.add(str(val).strip().upper())

        # 2. Retrieval Hit Rate
        if expected_set:
            hit_count = sum(1 for e in expected_set if e in retrieved_entities)
            retrieval_hit_rate = round(hit_count / len(expected_set), 4)
            retrieval_hit = (hit_count > 0)
        else:
            retrieval_hit_rate = 1.0 if retrieved_evidence else 0.0
            retrieval_hit = bool(retrieved_evidence)

        # 3. Retrieval Relevance (average similarity / confidence score)
        scores = []
        for ev in retrieved_evidence:
            if isinstance(ev, dict):
                s = ev.get("score") or ev.get("confidence")
                if s is not None:
                    try:
                        scores.append(float(s))
                    except (ValueError, TypeError):
                        pass
        retrieval_relevance = round(sum(scores) / len(scores), 4) if scores else 0.50

        # 4. Grounding Score & Citation Coverage
        resp = response_text or ""
        claims_grounded = True
        cited_count = 0

        # Check if mentioned entity IDs in response are in retrieved evidence
        mentioned_entities = set(re.findall(r"\b([PS]\d{3,5}|SUP\d{3,5})\b", resp, re.IGNORECASE))
        for me in mentioned_entities:
            if me.upper() not in retrieved_entities:
                claims_grounded = False
                break

        # Check evidence citation
        for ev in retrieved_evidence:
            val_str = str(ev.get("value") or ev.get("explanation") or "")[:50]
            if val_str and val_str.lower() in resp.lower():
                cited_count += 1

        citation_coverage = round(
            cited_count / max(1, len(retrieved_evidence)), 4
        ) if retrieved_evidence else 1.0
        grounding_score = 1.0 if claims_grounded else 0.50

        return {
            "query": query,
            "expected_entities": list(expected_set),
            "retrieved_entities": list(retrieved_entities),
            "retrieved_chunks": retrieved_chunks[:10],
            "retrieval_hit": retrieval_hit,
            "retrieval_hit_rate": retrieval_hit_rate,
            "retrieval_relevance": retrieval_relevance,
            "grounding_score": grounding_score,
            "citation_coverage": citation_coverage,
            "semantic_retrieval_latency_ms": round(semantic_latency_ms, 2),
            "hybrid_retrieval_latency_ms": round(total_latency_ms, 2),
            "evidence_count": len(retrieved_evidence),
        }

    @classmethod
    def compute_summary(
        cls,
        eval_cases: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Computes aggregate retrieval metrics across evaluated queries.
        """
        if not eval_cases:
            return {
                "total_retrieval_evaluations": 0,
                "retrieval_hit_rate": 0.0,
                "average_retrieval_relevance": 0.0,
                "average_grounding_score": 0.0,
                "average_citation_coverage": 0.0,
                "average_semantic_latency_ms": 0.0,
                "average_hybrid_latency_ms": 0.0,
            }

        n = len(eval_cases)
        return {
            "total_retrieval_evaluations": n,
            "retrieval_hit_rate": round(
                sum(c.get("retrieval_hit_rate", 0.0) for c in eval_cases) / n, 4
            ),
            "average_retrieval_relevance": round(
                sum(c.get("retrieval_relevance", 0.0) for c in eval_cases) / n, 4
            ),
            "average_grounding_score": round(
                sum(c.get("grounding_score", 0.0) for c in eval_cases) / n, 4
            ),
            "average_citation_coverage": round(
                sum(c.get("citation_coverage", 0.0) for c in eval_cases) / n, 4
            ),
            "average_semantic_latency_ms": round(
                sum(c.get("semantic_retrieval_latency_ms", 0.0) for c in eval_cases) / n, 2
            ),
            "average_hybrid_latency_ms": round(
                sum(c.get("hybrid_retrieval_latency_ms", 0.0) for c in eval_cases) / n, 2
            ),
        }
