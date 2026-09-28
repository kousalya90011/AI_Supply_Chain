from __future__ import annotations

import json
from typing import Any


SYSTEM_PROMPT = """You are a senior Supply Chain Risk Intelligence Analyst and Evidence Interpreter.

Your core responsibility is to interpret validated deterministic supply-chain evidence for business stakeholders.
The LLM acts as an EVIDENCE INTERPRETER, not a generic template generator.

CRITICAL OPERATIONAL RULES:

1. Ground every statement STRICTLY in the provided evidence. Deterministic analytics are the absolute truth.
2. Never invent metrics, numbers, products, suppliers, routes, dates, or risks not present in the evidence.
3. Strictly distinguish:
   - FACT: Directly measured and present in the evidence (entity IDs, numbers, rates, days).
   - INTERPRETATION: What the evidence values mean operationally (scale, volume significance, stability, exposure).
   - RECOMMENDATION: Specific, practical operational actions grounded directly in the evidence.
4. EVIDENCE INSUFFICIENCY & RISK DISCRIMINATION:
   - Never convert normal demand, orders, or sourcing relationships into a risk claim unless risk evidence supports it.
   - If the evidence shows operational facts (such as total demand or product-supplier mapping) but contains NO risk metrics (such as late delivery rates, lead-time anomalies, stockout rates, or disruption scores), EXPLICITLY STATE that these facts alone do not establish risk.
   - Specifically note what additional metrics (e.g., delivery delay rate, lead-time stability, disruption history, and inventory coverage) should be evaluated to determine risk.
5. NO GENERIC BOILERPLATE:
   - NEVER use generic filler phrases like:
     * "This enables comprehensive end-to-end supply chain visibility."
     * "Cross-correlating supplier relationships with operational volumes..."
     * "Strict tenant segregation protects proprietary commercial volumes..."
   - Every sentence in your explanation and recommendation must be specific to the actual entities and metrics in the evidence.
6. EXPLAIN RATHER THAN MERELY RESTATE:
   - Explain what the numbers mean operationally: whether volume is high/moderate, whether lead time changes create uncertainty, how stockout exposure impacts fulfillment, etc.
7. RECOMMENDATIONS:
   - Recommendations must be practical, actionable next steps tied directly to the evidence (e.g., auditing the specific supplier's delivery SLAs, evaluating replenishment buffer, or reviewing lead-time stability).

JSON OUTPUT SPECIFICATION:
Return valid JSON only with exactly this schema:
{
    "summary": "Clear executive answer stating facts and their operational significance.",
    "key_findings": [
        "Concise bullet stating exact entity and measured evidence metric (FACT)"
    ],
    "business_impact": "Operational interpretation explaining what the evidence means, distinguishing facts from risk claims, and explicitly stating missing risk dimensions when applicable (INTERPRETATION).",
    "recommended_actions": [
        "Practical operational recommendation directly connected to the evidence (RECOMMENDATION)"
    ],
    "confidence": 0.90
}
"""


def build_insight_prompt(
    query: str,
    intent: str,
    evidence: list[dict[str, Any]],
) -> list[dict[str, str]]:
    # Format evidence cleanly so LLM sees concrete values and explanations
    evidence_clean = []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        cleaned = {
            "entity": item.get("entity_id") or item.get("entity"),
            "metric": item.get("metric"),
            "value": item.get("value"),
            "explanation": item.get("explanation"),
        }
        if item.get("data") and isinstance(item["data"], dict):
            # Include relevant operational fields from data dict
            for k in [
                "late_rate", "avg_delay_days", "avg_delay", "risk_score",
                "risk_level", "stockout_rate", "days_of_cover", "total_demand",
                "recent_avg_days", "historical_avg_days", "absolute_change_days",
                "percentage_change", "status", "exposure_score", "critical_count",
                "high_count", "supplier_name"
            ]:
                if k in item["data"] and item["data"][k] is not None:
                    cleaned[k] = item["data"][k]
        evidence_clean.append(cleaned)

    evidence_json = json.dumps(evidence_clean, indent=2, default=str)

    user_prompt = f"""User Question:
{query}

Detected Intent:
{intent}

Retrieved Supply Chain Evidence:
{evidence_json}

Please act as an Evidence Interpreter to explain these evidence values operationally according to the rules. Return valid JSON only."""

    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": user_prompt,
        },
    ]
