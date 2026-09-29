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
        # Attempt repair for truncated closing braces
        repaired = text.rstrip()
        if repaired.count('"') % 2 != 0:
            repaired += '"'
        open_sq = repaired.count("[") - repaired.count("]")
        if open_sq > 0:
            repaired += "]" * open_sq
        open_curly = repaired.count("{") - repaired.count("}")
        if open_curly > 0:
            repaired += "}" * open_curly
        try:
            result = json.loads(repaired)
        except Exception:
            raise ValueError(f"LLM returned invalid JSON: {exc}")

    if not isinstance(result, dict):

        raise ValueError(
            "LLM output must be a JSON object."
        )

    # -------------------------------------------------
    # Safety scan: reject executable or injection code
    # -------------------------------------------------
    dangerous_patterns = [
        "<script",
        "javascript:",
        "drop table",
        "delete from",
        "eval(",
        "os.system(",
    ]
    lower_text = text.lower()
    for dp in dangerous_patterns:
        if dp in lower_text:
            raise ValueError(f"LLM output contains forbidden unsafe pattern: {dp}")

    # -------------------------------------------------
    # Validate expected fields
    # -------------------------------------------------

    summary = result.get("summary") or result.get("direct_answer") or result.get("answer")
    key_findings = result.get("key_findings", [])
    business_impact = (
        result.get("business_impact")
        or result.get("interpretation")
        or result.get("why_it_matters")
        or ""
    )
    recommended_actions = (
        result.get("recommended_actions")
        or result.get("recommendations")
        or []
    )
    confidence = result.get("confidence", 0.85)

    if not isinstance(summary, str) or not summary.strip():
        summary = "Operational supply chain analysis based on retrieved evidence."

    if not isinstance(key_findings, list):
        key_findings = [str(key_findings)] if key_findings else []

    if not isinstance(recommended_actions, list):
        recommended_actions = [str(recommended_actions)] if recommended_actions else []

    if not isinstance(business_impact, str):
        business_impact = str(business_impact) if business_impact else ""

    # Bound field lengths
    summary = summary[:2000].strip()
    business_impact = business_impact[:1500].strip()
    clean_findings = [str(item)[:500].strip() for item in key_findings[:10] if str(item).strip()]
    clean_actions = [str(item)[:500].strip() for item in recommended_actions[:6] if str(item).strip()]

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
        "key_findings": clean_findings,
        "business_impact": business_impact,
        "recommended_actions": clean_actions,
        "confidence": confidence
    }
