from __future__ import annotations

from typing import Any

from app.llm.query_classifier import QueryClassifier


class QueryRouter:

    def __init__(self):
        self.classifier = QueryClassifier()

    def route(self, query: str) -> dict[str, Any]:

        result = self.classifier.classify(query)

        intent = result.get("intent", "unknown")

        entity_type = result.get("entity_type")
        entity_id = result.get("entity_id")

        requires_entity = result.get(
            "requires_entity",
            False
        )

        return {
            "intent": intent,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "metric": result.get("metric"),
            "scope": result.get("scope"),
            "complexity": result.get("complexity", "simple"),
            "requires_entity": requires_entity,
            "confidence": result.get("confidence", 0.20),
            "method": result.get("method", "unknown")
        }