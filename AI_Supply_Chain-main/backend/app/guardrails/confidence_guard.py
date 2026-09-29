from __future__ import annotations

from typing import Any


class ConfidenceGuardrail:
    """
    Calibrates confidence scores by synthesizing deterministic analytics confidence,
    retrieval similarity, and LLM self-reported estimates.

    Ensures that low-evidence or weak-retrieval states cannot claim high certainty
    simply because an LLM returned a high self-reported confidence score.
    """

    @classmethod
    def calibrate(
        cls,
        *,
        evidence: list[dict[str, Any]],
        llm_confidence: float | None = None,
        planner_confidence: float | None = None,
        retrieval_mode: str = "structured",
        fallback_used: bool = False,
    ) -> dict[str, Any]:
        """
        Returns a calibrated composite confidence and detailed confidence breakdown.
        """
        if fallback_used:
            return {
                "calibrated_confidence": 0.20,
                "confidence_breakdown": {
                    "deterministic_analytics_confidence": 0.0,
                    "retrieval_similarity_confidence": 0.0,
                    "llm_self_reported_confidence": 0.0,
                    "calibration_reason": "fallback_engaged",
                },
            }

        # 1. Deterministic Analytics Confidence
        structured_evs = [
            e for e in evidence if isinstance(e, dict) and e.get("retrieval_method") == "structured"
        ]
        deterministic_conf = 1.0 if structured_evs else (0.80 if planner_confidence else 0.50)

        # 2. Retrieval Similarity Confidence
        semantic_evs = [
            e for e in evidence if isinstance(e, dict) and e.get("retrieval_method") == "semantic"
        ]
        if semantic_evs:
            scores = [float(e.get("confidence", 0.5)) for e in semantic_evs]
            retrieval_conf = round(sum(scores) / len(scores), 4)
        else:
            retrieval_conf = 1.0 if structured_evs else 0.0

        # 3. LLM self-reported confidence
        llm_conf = float(llm_confidence) if llm_confidence is not None else 0.85
        llm_conf = max(0.0, min(1.0, llm_conf))

        # Composite Calibration logic
        if len(evidence) == 0:
            final_conf = 0.15
            reason = "zero_evidence"
        elif retrieval_mode == "structured":
            # Deterministic calculations dominate
            final_conf = round(0.70 * deterministic_conf + 0.30 * llm_conf, 2)
            reason = "grounded_in_deterministic_analytics"
        elif retrieval_mode == "semantic":
            # Semantic retrieval bounds the certainty
            final_conf = round(0.60 * retrieval_conf + 0.40 * min(retrieval_conf + 0.15, llm_conf), 2)
            reason = "grounded_in_semantic_retrieval"
        else:  # hybrid
            final_conf = round(0.50 * deterministic_conf + 0.30 * retrieval_conf + 0.20 * llm_conf, 2)
            reason = "hybrid_grounded_evidence"

        # Cap confidence if retrieval was weak
        if semantic_evs and retrieval_conf < 0.25 and not structured_evs:
            final_conf = min(final_conf, 0.50)
            reason = "capped_due_to_low_semantic_similarity"

        return {
            "calibrated_confidence": round(final_conf, 2),
            "confidence_breakdown": {
                "deterministic_analytics_confidence": round(deterministic_conf, 2),
                "retrieval_similarity_confidence": round(retrieval_conf, 2),
                "llm_self_reported_confidence": round(llm_conf, 2),
                "calibration_reason": reason,
            },
        }
