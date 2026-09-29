from __future__ import annotations

import logging
from typing import Any
from app.config import settings
from app.guardrails.schemas import GuardrailResult, GuardrailStatus
from app.guardrails.input_guard import InputGuardrail
from app.guardrails.scope_guard import QueryScopeGuardrail
from app.guardrails.rag_guard import RAGRetrievalGuardrail
from app.guardrails.output_guard import OutputGuardrail
from app.guardrails.confidence_guard import ConfidenceGuardrail

logger = logging.getLogger(__name__)


class GuardrailService:
    """
    Unified application-level guardrail service coordinating:
    1. Input Validation & Prompt Injection Defense (InputGuardrail)
    2. Scope & Domain Bounding (QueryScopeGuardrail)
    3. RAG Retrieval & Top-K Bounding (RAGRetrievalGuardrail)
    4. Output Safety & Evidence Grounding Consistency (OutputGuardrail)
    5. Calibrated Confidence Scoring (ConfidenceGuardrail)
    """

    def __init__(self) -> None:
        self.input_guard = InputGuardrail(max_length=settings.MAX_QUERY_LENGTH)
        self.scope_guard = QueryScopeGuardrail()
        self.rag_guard = RAGRetrievalGuardrail(
            max_top_k=settings.MAX_TOP_K,
            max_evidence=settings.MAX_EVIDENCE_ITEMS,
            min_score=settings.MIN_RETRIEVAL_SCORE,
        )
        self.output_guard = OutputGuardrail()
        self.confidence_guard = ConfidenceGuardrail()

        # Telemetry counters for system evaluation
        self.metrics = {
            "total_requests": 0,
            "input_rejections": 0,
            "prompt_injections_blocked": 0,
            "scope_rejections": 0,
            "unauthorized_retrieval_blocked": 0,
            "hallucinations_blocked": 0,
            "fallback_triggers": 0,
        }

    def check_input(self, query: str | None) -> GuardrailResult:
        """Runs input validation and prompt injection detection."""
        self.metrics["total_requests"] += 1
        res = self.input_guard.validate(query)
        if not res.passed:
            self.metrics["input_rejections"] += 1
            if res.reason == "prompt_injection_detected":
                self.metrics["prompt_injections_blocked"] += 1
        return res

    def check_scope(self, query: str) -> GuardrailResult:
        """Verifies that query is within supported supply-chain capabilities."""
        res = self.scope_guard.validate(query)
        if not res.passed:
            self.metrics["scope_rejections"] += 1
            self.metrics["fallback_triggers"] += 1
        return res

    def check_output(
        self,
        parsed_output: dict[str, Any],
        evidence: list[dict[str, Any]],
        query: str,
    ) -> GuardrailResult:
        """Validates schema safety, code execution boundaries, and entity consistency."""
        schema_res = self.output_guard.validate_schema_and_safety(parsed_output)
        if not schema_res.passed:
            self.metrics["fallback_triggers"] += 1
            return schema_res

        entity_res = self.output_guard.validate_entity_consistency(parsed_output, evidence, query)
        if not entity_res.passed:
            self.metrics["hallucinations_blocked"] += 1
            self.metrics["fallback_triggers"] += 1
            return entity_res

        return schema_res

    def calibrate_confidence(
        self,
        *,
        evidence: list[dict[str, Any]],
        llm_confidence: float | None = None,
        planner_confidence: float | None = None,
        retrieval_mode: str = "structured",
        fallback_used: bool = False,
    ) -> dict[str, Any]:
        """Calculates multi-source calibrated confidence."""
        return self.confidence_guard.calibrate(
            evidence=evidence,
            llm_confidence=llm_confidence,
            planner_confidence=planner_confidence,
            retrieval_mode=retrieval_mode,
            fallback_used=fallback_used,
        )

    def get_metrics(self) -> dict[str, Any]:
        """Returns snapshot of guardrail trigger metrics."""
        total = max(1, self.metrics["total_requests"])
        return {
            **self.metrics,
            "input_rejection_rate": round(self.metrics["input_rejections"] / total, 4),
            "prompt_injection_block_rate": round(self.metrics["prompt_injections_blocked"] / total, 4),
            "unsupported_query_rate": round(self.metrics["scope_rejections"] / total, 4),
            "hallucination_block_rate": round(self.metrics["hallucinations_blocked"] / total, 4),
        }
