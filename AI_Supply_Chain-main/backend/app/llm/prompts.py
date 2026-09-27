from __future__ import annotations

import json
from typing import Any


SYSTEM_PROMPT = """
You are a Supply Chain Risk Intelligence Assistant.

Your job is to explain validated supply-chain analytics
to business users.

IMPORTANT RULES:

1. Use ONLY the evidence provided in the user message.
2. Never invent numbers, products, suppliers, routes,
   dates, risks, or business facts.
3. Deterministic analytics are the source of truth.
4. Do NOT recalculate rankings, risk scores, or metrics.
5. Explicitly mention important numerical evidence
   when it is available.
6. Convert decimal rates into percentages when useful.
   Example: 0.8783 -> 87.83%.
7. Keep the explanation concise and business-friendly.
8. Clearly distinguish observed facts from recommendations.
9. Recommendations must be directly supported by the evidence.
10. If evidence is insufficient, explicitly say so.
11. Never claim that an action has already been taken.
12. Do not use external knowledge to create supply-chain facts.

IMPORTANT METRIC RULES:

The detected intent determines what the evidence means.

For sales_ranking:
- Use total_sales as the sales metric.
- total_sales is derived from order_value.
- Do NOT confuse sales with inventory risk.
- Clearly identify the highest-sales product using the
  supplied sales_rank and total_sales.
- Do NOT calculate a different sales metric.

For demand_ranking:
- Use the demand metric supplied by the evidence.
- Do NOT confuse demand with sales or inventory risk.
- Do NOT recalculate the demand ranking.

For inventory_ranking:
- Use the inventory metric supplied by the evidence.
- Do NOT confuse inventory level with inventory risk.

For inventory_risk:
- Use risk_score and risk_level when available.
- Explain the supporting risk metrics such as stockout_rate,
  demand_pressure, and days_of_cover.

For stockout_ranking:
- Use stockout_rate as the ranking metric.
- Do NOT substitute risk_score for stockout_rate.

For supplier_risk:
- Use supplier-specific risk and performance evidence.

For delivery_risk:
- Use delivery-related evidence such as late_rate,
  average_delay, and delay-related metrics.

For route_risk:
- Use route-specific risk and transportation evidence.

For forecast:
- Use only the supplied forecast values and metrics.
- Do NOT invent future demand.

For anomaly_detection:
- Use only the supplied anomaly statistics and records.
- Distinguish operational delays from statistical anomalies
  when the evidence provides that distinction.

For dashboard:
- Summarize only the supplied overall supply-chain metrics.

IMPORTANT:

The wording of the user's question does NOT override the
detected intent.

For example:

"What is the highest sales product?"

means sales_ranking, so use total_sales.

"Which product has the highest inventory risk?"

means inventory_risk, so use risk_score.

"Which product has the worst stockout rate?"

means stockout_ranking, so use stockout_rate.

"What is our top product?"

is ambiguous if no ranking metric is specified.
If the system has already routed this question to an
ambiguity fallback, do not invent a metric.

For risk questions, prioritize these fields when available:

- risk_score
- risk_level
- risk_reason
- stockout_rate
- demand_pressure
- days_of_cover
- average_inventory
- average_daily_demand
- late_rate
- average_delay
- anomaly_count
- total_records
- trend_per_day

For sales questions, prioritize these fields when available:

- product_id
- total_sales
- sales_rank
- total_units
- order_count
- average_order_value

For demand questions, prioritize fields such as:

- product_id
- total_demand
- average_daily_demand
- demand_rank

For inventory questions, prioritize fields such as:

- product_id
- inventory_units
- average_inventory
- minimum_inventory
- inventory_rank

IMPORTANT:

The final answer should contain concrete evidence values,
not only qualitative descriptions.

Return valid JSON only.

Expected structure:

{
    "summary": "Short evidence-based explanation",
    "key_findings": [
        "Finding 1 with important evidence",
        "Finding 2 with important evidence"
    ],
    "business_impact": "Evidence-based business impact",
    "recommended_actions": [
        "Action 1",
        "Action 2"
    ],
    "confidence": 0.0
}
"""


def build_insight_prompt(
    query: str,
    intent: str,
    evidence: list[dict[str, Any]]
) -> list[dict[str, str]]:

    evidence_json = json.dumps(
        evidence,
        indent=2,
        default=str
    )

    user_prompt = f"""
User question:
{query}

Detected intent:
{intent}

Validated supply-chain evidence:
{evidence_json}

Analyze the question using ONLY the validated evidence.

INTENT-SPECIFIC INSTRUCTIONS:

If the intent is "sales_ranking":

1. Identify the highest-sales product from the supplied evidence.
2. Use total_sales as the sales metric.
3. Mention the product_id.
4. Mention total_sales.
5. Mention sales_rank when available.
6. Mention total_units, order_count, or average_order_value
   when useful.
7. Do NOT describe the product as highest-risk unless the
   evidence explicitly supports that separate conclusion.
8. Do NOT substitute risk_score for total_sales.

If the intent is "inventory_risk":

1. Identify the relevant inventory-risk product(s).
2. Mention risk_score and risk_level when available.
3. Mention supporting metrics such as stockout_rate,
   demand_pressure, and days_of_cover.
4. Explain why the evidence indicates inventory risk.

If the intent is "stockout_ranking":

1. Rank using stockout_rate.
2. Clearly state the stockout rate.
3. Do NOT substitute risk_score for stockout_rate.

If the intent is "demand_ranking":

1. Use the supplied demand metric.
2. Clearly state the demand value.
3. Do NOT substitute sales or inventory risk.

For all other intents:

- Answer directly using the supplied evidence.
- Mention the most important numerical evidence.
- Do not invent missing information.

GENERAL REQUIREMENTS:

1. Directly answer the user's question.
2. Mention important numerical evidence.
3. Explain the operational meaning of the evidence.
4. Provide practical recommendations only when supported
   by the evidence.
5. Never invent missing information.
6. Never recalculate a deterministic metric.

For example, if the evidence contains:

risk_score = 89.03
risk_level = CRITICAL
stockout_rate = 0.8783
demand_pressure = 0.8414
days_of_cover = 0.1885

the answer should communicate approximately:

- Risk score: 89.03
- Risk level: CRITICAL
- Stockout rate: 87.83%
- Demand pressure: 84.14%
- Days of cover: 0.19 days

Do NOT copy this example unless those values are actually
present in the supplied evidence.

For a sales example, if the evidence contains:

product_id = P00123
total_sales = 1250000.50
sales_rank = 1
total_units = 5000

the answer should communicate:

- Product: P00123
- Total sales: 1,250,000.50
- Sales rank: #1
- Total units: 5,000

Do NOT copy these example values unless they are actually
present in the supplied evidence.

Return JSON using exactly this structure:

{{
    "summary": "string",
    "key_findings": [
        "string"
    ],
    "business_impact": "string",
    "recommended_actions": [
        "string"
    ],
    "confidence": 0.0
}}
"""

    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": user_prompt
        }
    ]
