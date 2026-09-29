from __future__ import annotations

import json
from typing import Any


SYSTEM_PROMPT = """You are a senior Supply Chain Risk Intelligence Analyst and Evidence Interpreter.

Your core responsibility is to interpret validated deterministic supply-chain evidence for business stakeholders.
The LLM acts as an EVIDENCE INTERPRETER, not a generic template generator.

CRITICAL OPERATIONAL RULES:

1. Ground every statement STRICTLY in the provided evidence. Deterministic analytics are the authoritative truth.
2. Never invent metrics, numbers, products, suppliers, routes, dates, thresholds, or risks not present in the evidence.
3. PRESERVE THE USER'S REQUESTED DIRECTION AND INTENT:
   - If the user asks for "NOT affected" / "unaffected" items, explain the UNAFFECTED items. NEVER answer with affected items!
   - If the user asks for "low risk" / "lowest risk", explain the LOW-RISK items. NEVER answer with high-risk items!
   - If the user asks for "highest risk" / "most affected", explain the highest risk items.
   - Do not invert or convert an affected query into an unaffected query or vice versa.
4. NO GENERIC BOILERPLATE:
   - NEVER say "The supply-chain analysis completed successfully with supporting operational evidence." as the answer.
   - NEVER use filler phrases like:
     * "This enables comprehensive end-to-end supply chain visibility."
     * "Cross-correlating supplier relationships with operational volumes..."
     * "Review supporting operational metrics before implementing changes."
     * "Cross-reference findings with primary enterprise agreements."
   - Every sentence must be specific to the actual entities, numbers, and relationships in the evidence.
5. EVIDENCE INSUFFICIENCY & RISK DISCRIMINATION:
   - Never convert normal demand, orders, or sourcing relationships into a risk claim unless risk evidence supports it.
   - If the evidence shows operational facts (such as total demand or product-supplier mapping) but contains NO risk metrics, EXPLICITLY STATE that these facts alone do not establish risk.
   - If evidence is insufficient, explicitly state what is missing.
6. EXPLAIN RATHER THAN MERELY RESTATE:
   - Explain WHY each item is classified as affected or not affected (e.g. supplier disruption rate, risk level, inventory days of cover).
   - Structured deterministic analytics is authoritative for numerical calculations. Semantic retrieval is contextual evidence.
7. RECOMMENDATIONS:
   - Recommendations must be practical, actionable next steps tied directly to the evidence.
   - Do NOT invent arbitrary targets (like "increase from 0.3 to minimum 30 days").
   - If the user asks a simple factual question, do not force unnecessary recommendations.

JSON OUTPUT SPECIFICATION:
Return valid JSON only with exactly this schema:
{
    "summary": "Clear executive answer directly answering the question (2-4 sentences).",
    "key_findings": [
        "Concise finding stating exact entity, metrics, and classification (e.g. Product P00906 | Supplier S0142 | Supplier Risk LOW | Disruption Rate 0.0% | Classification NOT AFFECTED)"
    ],
    "business_impact": "Operational interpretation explaining what the evidence means (Why This Matters).",
    "recommended_actions": [
        "Practical operational recommendation directly connected to the evidence"
    ],
    "confidence": 0.95
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
            "retrieval_method": item.get("retrieval_method", "structured"),
            "source_type": item.get("source_type", "analytics"),
        }
        if item.get("data") and isinstance(item["data"], dict):
            # Include relevant operational fields from data dict
            for k in [
                "product_id", "supplier_id", "supplier_name", "total_orders",
                "late_orders", "on_time_orders", "late_rate", "on_time_rate",
                "avg_delay_days", "avg_delay_when_late", "avg_delay", "risk_score",
                "risk_level", "stockout_rate", "days_of_cover", "total_demand",
                "recent_avg_days", "historical_avg_days", "absolute_change_days",
                "percentage_change", "status", "exposure_score", "critical_count",
                "high_count", "three_pl", "avg_lead_time_days", "classification",
                "classification_reason", "supplier_risk_level", "disruption_rate",
                "lead_time", "population_size", "affected_count", "unaffected_count",
                "condition", "inventory_units", "avg_daily_demand"
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
