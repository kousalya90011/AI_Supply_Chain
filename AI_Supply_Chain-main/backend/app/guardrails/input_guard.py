from __future__ import annotations

import re
from typing import Any
from app.config import settings
from app.guardrails.schemas import GuardrailResult


class InputGuardrail:
    """
    Validates and sanitizes user input prior to semantic planning,
    retrieval, or LLM invocation.

    Enforces:
    - Non-empty input validation & whitespace trimming.
    - Bounded query length via configurable MAX_QUERY_LENGTH.
    - Malformed input and excessive character repetition detection.
    - Multi-layered prompt injection & system jailbreak defense,
      without blocking legitimate supply-chain domain terminology.
    """

    # Prompt injection patterns (case-insensitive)
    PROMPT_INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?(previous|prior|system|earlier)\s+(instructions|prompts|rules|commands)",
        r"disregard\s+(all\s+)?(previous|prior|system|earlier)\s+(instructions|prompts|rules)",
        r"(reveal|show|display|print|leak|output)\s+(your\s+)?(system\s+prompt|hidden\s+instructions|developer\s+mode|master\s+prompt)",
        r"bypass\s+(access\s+control|security|auth|authorization|supplier\s+scop(e|ing)|guardrails?)",
        r"(give|show|dump|leak)\s+(me\s+)?(another|other|competitor|all)\s+supplier('?s)?\s+(private|secret|confidential|restricted)",
        r"you\s+are\s+now\s+(in\s+)?(dan|developer\s+mode|unrestricted|jailbreak|chaos\s+mode)",
        r"system\s*:\s*override\b",
        r"<\s*script[^>]*>",
        r"drop\s+table\b",
    ]

    def __init__(self, max_length: int | None = None) -> None:
        self.max_length = max_length or getattr(settings, "MAX_QUERY_LENGTH", 500)
        self._compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.PROMPT_INJECTION_PATTERNS
        ]

    def validate(self, query: str | None) -> GuardrailResult:
        # 1. Null or empty validation
        if query is None or not str(query).strip():
            return GuardrailResult(
                passed=False,
                guardrail_name="InputGuardrail",
                action="reject",
                reason="empty_query",
                user_message="Please enter a valid supply-chain query.",
            )

        trimmed = str(query).strip()

        # 2. Maximum query length check
        if len(trimmed) > self.max_length:
            return GuardrailResult(
                passed=False,
                guardrail_name="InputGuardrail",
                action="reject",
                reason="query_too_long",
                user_message=f"Query exceeds the maximum allowed limit of {self.max_length} characters. Please submit a more focused inquiry.",
                metadata={"length": len(trimmed), "max_length": self.max_length},
            )

        # 3. Detect unprintable/binary control characters
        non_printable = [c for c in trimmed if ord(c) < 32 and c not in ("\n", "\r", "\t")]
        if len(non_printable) > 2:
            return GuardrailResult(
                passed=False,
                guardrail_name="InputGuardrail",
                action="reject",
                reason="malformed_control_characters",
                user_message="The query contains invalid or malformed characters.",
            )

        # 4. Detect excessive repeated characters (e.g. 'aaaaa...' > 30 times)
        if re.search(r"(.)\1{30,}", trimmed):
            return GuardrailResult(
                passed=False,
                guardrail_name="InputGuardrail",
                action="reject",
                reason="repeated_character_spam",
                user_message="Malformed input detected: excessive repeated characters.",
            )

        # 5. Prompt injection / jailbreak instruction detection
        for pattern in self._compiled_patterns:
            match = pattern.search(trimmed)
            if match:
                return GuardrailResult(
                    passed=False,
                    guardrail_name="InputGuardrail",
                    action="reject",
                    reason="prompt_injection_detected",
                    user_message="Security policy notice: Instruction overrides or system prompt requests are not permitted.",
                    metadata={"matched_pattern": pattern.pattern, "matched_text": match.group(0)},
                )

        return GuardrailResult(
            passed=True,
            guardrail_name="InputGuardrail",
            action="allow",
            sanitized_query=trimmed,
            metadata={"length": len(trimmed)},
        )
