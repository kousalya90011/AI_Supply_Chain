from __future__ import annotations

import json
from typing import Any


def parse_llm_output(
    content: str
) -> dict[str, Any]:

    if not content or not content.strip():
        raise ValueError(
            "LLM returned empty content."
        )

    text = content.strip()

    # -------------------------------------------------
    # Remove markdown JSON fences if present
    # -------------------------------------------------

    if text.startswith("```json"):
        text = text[7:]

    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    # -------------------------------------------------
    # Parse JSON
    # -------------------------------------------------

    try:

        result = json.loads(text)

    except json.JSONDecodeError as exc:

        raise ValueError(
            f"LLM returned invalid JSON: {exc}"
        )

    if not isinstance(result, dict):

        raise ValueError(
            "LLM output must be a JSON object."
        )

    # -------------------------------------------------
    # Validate expected fields
    # -------------------------------------------------

    summary = result.get(
        "summary"
    )

    key_findings = result.get(
        "key_findings",
        []
    )

    business_impact = result.get(
        "business_impact",
        ""
    )

    recommended_actions = result.get(
        "recommended_actions",
        []
    )

    confidence = result.get(
        "confidence",
        0.0
    )

    if not isinstance(summary, str):
        raise ValueError(
            "Invalid 'summary' field."
        )

    if not isinstance(key_findings, list):
        raise ValueError(
            "Invalid 'key_findings' field."
        )

    if not isinstance(recommended_actions, list):
        raise ValueError(
            "Invalid 'recommended_actions' field."
        )

    if not isinstance(business_impact, str):
        raise ValueError(
            "Invalid 'business_impact' field."
        )

    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0

    confidence = max(
        0.0,
        min(1.0, confidence)
    )

    return {
        "summary": summary,
        "key_findings": [
            str(item)
            for item in key_findings
        ],
        "business_impact": business_impact,
        "recommended_actions": [
            str(item)
            for item in recommended_actions
        ],
        "confidence": confidence
    }
