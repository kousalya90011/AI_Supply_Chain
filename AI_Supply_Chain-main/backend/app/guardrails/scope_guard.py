from __future__ import annotations

import re
from typing import Any
from app.guardrails.schemas import GuardrailResult


class QueryScopeGuardrail:
    """
    Validates that a user query falls within supported supply-chain
    risk intelligence and control tower capabilities.

    Explicitly intercepts out-of-domain inquiries (e.g., sports scores, recipes,
    generic trivia, offensive or hacking requests) to prevent LLM hallucinations
    and route directly to a safe, controlled response.
    """

    SUPPORTED_CAPABILITIES_MESSAGE = (
        "That request is outside the supported supply-chain analysis capabilities. "
        "I can analyze supplier risk, inventory stockout runways, delivery performance, "
        "lead-time anomalies, demand forecasts, and route disruptions."
    )

    # Clear out-of-domain triggers
    OUT_OF_DOMAIN_PATTERNS = [
        r"\b(cricket|football|soccer|baseball|basketball|nba|ipl|fifa)\b.*(score|match|winner|schedule|cup)",
        r"\b(today('?s)?|live)\s+(cricket|football|soccer|game|match)\s+score\b",
        r"\b(recipe|cook|bake|ingredients)\s+for\b",
        r"\b(who\s+won|score\s+of|match\s+result)\b",
        r"\b(write\s+(a\s+)?(poem|song|story|joke|essay|code|script\s+to\s+hack))\b",
        r"\b(capital\s+of|president\s+of|prime\s+minister\s+of|weather\s+in|horoscope)\b",
        r"\b(tell\s+me\s+a\s+joke|make\s+me\s+laugh)\b",
    ]

    # Supply-chain domain terminology indicators
    SUPPLY_CHAIN_INDICATORS = [
        "supplier", "vendor", "product", "sku", "item", "inventory", "stock",
        "stockout", "runway", "delivery", "late", "delay", "on_time", "on-time",
        "lead_time", "lead time", "transit", "route", "carrier", "3pl", "logistics",
        "order", "purchase order", "po", "demand", "forecast", "predict", "sales",
        "risk", "disruption", "anomaly", "anomalies", "bottleneck", "tier", "unit_cost",
        "unit cost", "offer", "discount", "fulfill", "fulfillment", "supply", "capacity",
        "dashboard", "control tower", "score", "metric", "performance", "p0", "s0"
    ]

    def __init__(self) -> None:
        self._compiled_out_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.OUT_OF_DOMAIN_PATTERNS
        ]

    def validate(self, query: str) -> GuardrailResult:
        normalized = (query or "").strip().lower()

        # 1. Check for explicit out-of-domain triggers
        for pattern in self._compiled_out_patterns:
            if pattern.search(normalized):
                return GuardrailResult(
                    passed=False,
                    guardrail_name="QueryScopeGuardrail",
                    action="fallback",
                    reason="out_of_domain_query",
                    user_message=self.SUPPORTED_CAPABILITIES_MESSAGE,
                    metadata={"pattern": pattern.pattern},
                )

        # 2. Check for supply chain keywords or entity pattern identifiers (e.g. P00003, S0142)
        has_entity_pattern = bool(re.search(r"\b[ps]\d{3,5}\b", normalized, re.IGNORECASE))
        has_domain_keyword = any(kw in normalized for kw in self.SUPPLY_CHAIN_INDICATORS)

        # Allow basic greetings and conversational queries to proceed to planner
        is_greeting = any(normalized.startswith(g) for g in ["hi", "hello", "hey", "help", "what can you do"])

        if not (has_entity_pattern or has_domain_keyword or is_greeting):
            return GuardrailResult(
                passed=False,
                guardrail_name="QueryScopeGuardrail",
                action="fallback",
                reason="unsupported_supply_chain_scope",
                user_message=self.SUPPORTED_CAPABILITIES_MESSAGE,
            )

        return GuardrailResult(
            passed=True,
            guardrail_name="QueryScopeGuardrail",
            action="allow",
        )
