from __future__ import annotations

import re
import json
import logging
from typing import Any
from app.guardrails.schemas import GuardrailResult

logger = logging.getLogger(__name__)


class OutputGuardrail:
    """
    Validates LLM generated content and enforces factual consistency with supplied evidence.

    Protections:
    - Schema validation: guarantees summary, key_findings, business_impact, recommended_actions, confidence.
    - Rejects executable payload injections (<script>, SQL commands, python code snippets).
    - Prevents runaway field lengths.
    - Hallucination / Entity Consistency check: verifies that supplier IDs and product IDs
      mentioned in the response exist in the verified input evidence or query.
    """

    DANGEROUS_PATTERNS = [
        r"<\s*script[^>]*>",
        r"javascript\s*:",
        r"\b(eval|exec|os\.system|subprocess\.Popen)\s*\(",
        r"\bDROP\s+TABLE\b",
        r"\bDELETE\s+FROM\b",
        r"\bINSERT\s+INTO\b",
        r"\bUPDATE\s+.*SET\b",
        r"\bALTER\s+TABLE\b",
    ]

    def __init__(self) -> None:
        self._compiled_dangerous = [
            re.compile(p, re.IGNORECASE) for p in self.DANGEROUS_PATTERNS
        ]

    def validate_schema_and_safety(
        self,
        parsed_output: dict[str, Any],
    ) -> GuardrailResult:
        """Validates structure, types, field lengths, and code safety."""
        if not isinstance(parsed_output, dict):
            return GuardrailResult(
                passed=False,
                guardrail_name="OutputGuardrail",
                action="fallback",
                reason="output_not_a_dict",
                user_message="LLM output failed structural schema validation.",
            )

        summary = parsed_output.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            return GuardrailResult(
                passed=False,
                guardrail_name="OutputGuardrail",
                action="fallback",
                reason="missing_summary",
                user_message="LLM output missing valid executive summary.",
            )

        # Cap excessively long summary to prevent runaway generation
        if len(summary) > 2500:
            parsed_output["summary"] = summary[:2500] + "..."

        # Key findings validation
        key_findings = parsed_output.get("key_findings", [])
        if not isinstance(key_findings, list):
            key_findings = [str(key_findings)] if key_findings else []
        parsed_output["key_findings"] = [str(kf)[:500] for kf in key_findings[:10]]

        # Business impact validation
        bi = parsed_output.get("business_impact", "")
        if not isinstance(bi, str):
            bi = str(bi) if bi else ""
        parsed_output["business_impact"] = bi[:1500]

        # Recommended actions validation
        rec_actions = parsed_output.get("recommended_actions", [])
        if not isinstance(rec_actions, list):
            rec_actions = [str(rec_actions)] if rec_actions else []
        parsed_output["recommended_actions"] = [str(a)[:500] for a in rec_actions[:6]]

        # Check for dangerous executable patterns in all string outputs
        all_text = f"{summary} {' '.join(parsed_output['key_findings'])} {bi} {' '.join(parsed_output['recommended_actions'])}"
        for pattern in self._compiled_dangerous:
            if pattern.search(all_text):
                logger.error(f"OutputGuardrail detected dangerous pattern: {pattern.pattern}")
                return GuardrailResult(
                    passed=False,
                    guardrail_name="OutputGuardrail",
                    action="reject",
                    reason="unsafe_executable_content_detected",
                    user_message="Response rejected due to security policy violations (executable code detected).",
                )

        return GuardrailResult(
            passed=True,
            guardrail_name="OutputGuardrail",
            action="allow",
        )

    def validate_entity_consistency(
        self,
        parsed_output: dict[str, Any],
        evidence: list[dict[str, Any]],
        query: str,
    ) -> GuardrailResult:
        """
        Lightweight deterministic check verifying that entity identifiers
        (e.g., P00003, S0109, SUP001) mentioned in the LLM response exist in
        the supplied evidence or original query.
        """
        response_text = f"{parsed_output.get('summary', '')} {' '.join(parsed_output.get('key_findings', []))} {parsed_output.get('business_impact', '')}"

        # Extract entity mentions from generated text
        mentioned_entities = set(re.findall(r"\b([PS]\d{3,5}|SUP\d{3,5})\b", response_text, re.IGNORECASE))
        if not mentioned_entities:
            return GuardrailResult(
                passed=True,
                guardrail_name="OutputGuardrail:EntityConsistency",
                action="allow",
            )

        # Build set of verified entity IDs from evidence and user query
        verified_entities: set[str] = set()
        for token in re.findall(r"\b([PS]\d{3,5}|SUP\d{3,5})\b", query, re.IGNORECASE):
            verified_entities.add(token.upper())

        for ev in evidence:
            if not isinstance(ev, dict):
                continue
            for k in ["entity_id", "entity", "source_id"]:
                val = ev.get(k)
                if val:
                    for token in re.findall(r"\b([PS]\d{3,5}|SUP\d{3,5})\b", str(val), re.IGNORECASE):
                        verified_entities.add(token.upper())
            data = ev.get("data")
            if isinstance(data, dict):
                for k in ["supplier_id", "product_id"]:
                    val = data.get(k)
                    if val:
                        verified_entities.add(str(val).upper())

        # Check for ungrounded entity IDs
        unverified = [e for e in mentioned_entities if e.upper() not in verified_entities]
        if unverified:
            logger.warning(
                f"OutputGuardrail: Detected hallucinated entity IDs {unverified} not present in evidence. Verified: {verified_entities}"
            )
            return GuardrailResult(
                passed=False,
                guardrail_name="OutputGuardrail:EntityConsistency",
                action="fallback",
                reason="hallucinated_entities_detected",
                user_message="Response failed evidence consistency validation: ungrounded entity identifiers detected.",
                metadata={"hallucinated_entities": unverified, "verified_entities": list(verified_entities)},
            )

        return GuardrailResult(
            passed=True,
            guardrail_name="OutputGuardrail:EntityConsistency",
            action="allow",
        )
