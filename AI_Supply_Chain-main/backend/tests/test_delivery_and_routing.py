from __future__ import annotations

import pytest
from app.llm.query_classifier import QueryClassifier
from app.services.query_service import QueryService


def test_query_classification_intents():
    qc = QueryClassifier()

    cases = [
        ("What is my performance in delivery?", "delivery_performance"),
        ("How many orders were late?", "delivery_performance"),
        ("What is the late delivery rate?", "delivery_performance"),
        ("Which suppliers have high delivery risk?", "supplier_delivery_risk"),
        ("Which suppliers have risk?", "supplier_risk"),
        ("Which suppliers are causing delivery delays?", "supplier_delivery_risk"),
        ("Why are deliveries delayed?", "delivery_analysis"),
        ("Why is product P00003 at inventory risk?", "inventory_risk"),
        ("Forecast demand for product P00003", "forecast"),
    ]

    for query, expected_intent in cases:
        res = qc.classify(query)
        actual_intent = res.get("intent")
        assert (
            actual_intent == expected_intent
        ), f"Query '{query}' expected intent '{expected_intent}', got '{actual_intent}'"


def test_delivery_performance_pipeline_execution():
    qs = QueryService()
    res = qs.query("What is my performance in delivery?")

    assert res["status"] == "success"
    assert res["intent"] == "delivery_performance"
    assert len(res["evidence"]) > 0

    # Confirm network delivery metrics were retrieved dynamically
    network_ev = [ev for ev in res["evidence"] if ev.get("data", {}).get("scope") == "network"]
    assert len(network_ev) == 1
    data = network_ev[0]["data"]
    assert data["total_orders"] == 200000
    assert data["late_orders"] > 0
    assert 0.0 < data["late_rate"] < 1.0
    assert 0.0 < data["on_time_rate"] < 1.0

    # Confirm executive summary contains the actual numbers
    answer = res["answer"]
    assert "Across the analyzed orders, delivery performance is" in answer
    assert "late orders out of 200,000 total orders" in answer
    assert "The late rate is" in answer
    assert "Total orders:" in answer
    assert "Late orders:" in answer


def test_critical_rule_insufficient_evidence():
    qs = QueryService()
    # Query for a non-existent supplier
    res = qs.query("Investigate supplier S99999999")

    # Critical rule: Never return Evidence Records = 0 and Status = success
    if len(res.get("evidence", [])) == 0:
        assert res["status"] != "success"
        assert res["status"] in {"insufficient_evidence", "denied", "fallback", "clarification_required", "unsupported"}
