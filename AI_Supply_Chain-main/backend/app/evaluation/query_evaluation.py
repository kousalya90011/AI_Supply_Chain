from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.agents.router import QueryRouter


class QueryEvaluationEngine:

    def __init__(self):
        self.router = QueryRouter()

        self.project_root = Path(__file__).resolve().parents[3]

        self.benchmark_path = (
            self.project_root
            / "evaluation"
            / "benchmark_queries.json"
        )

    def load_benchmarks(self) -> list[dict[str, Any]]:
        if not self.benchmark_path.exists():
            raise FileNotFoundError(
                f"Benchmark file not found: {self.benchmark_path}"
            )

        with open(
            self.benchmark_path,
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)

    def evaluate_routing(self) -> dict[str, Any]:

        benchmarks = self.load_benchmarks()

        results = []

        correct_intent = 0
        correct_entity_type = 0
        correct_entity_id = 0

        for item in benchmarks:

            query = item["query"]

            actual = self.router.route(query)

            intent_correct = (
                actual["intent"]
                == item["expected_intent"]
            )

            entity_type_correct = (
                actual["entity_type"]
                == item["expected_entity_type"]
            )

            expected_entity_id = item.get(
                "expected_entity_id"
            )

            entity_id_correct = (
                actual.get("entity_id")
                == expected_entity_id
            )

            if intent_correct:
                correct_intent += 1

            if entity_type_correct:
                correct_entity_type += 1

            if entity_id_correct:
                correct_entity_id += 1

            results.append({
                "query": query,
                "expected_intent": item["expected_intent"],
                "actual_intent": actual["intent"],
                "intent_correct": intent_correct,
                "expected_entity_type": item.get("expected_entity_type"),
                "actual_entity_type": actual.get("entity_type"),
                "entity_type_correct": entity_type_correct,
                "expected_entity_id": expected_entity_id,
                "actual_entity_id": actual.get("entity_id"),
                "entity_id_correct": entity_id_correct
            })

        total = len(benchmarks)

        return {
            "total_queries": total,
            "intent_accuracy": round(
                correct_intent / total,
                4
            ),
            "entity_type_accuracy": round(
                correct_entity_type / total,
                4
            ),
            "entity_id_accuracy": round(
                correct_entity_id / total,
                4
            ),
            "results": results
        }
    