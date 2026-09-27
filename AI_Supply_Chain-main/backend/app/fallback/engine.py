from __future__ import annotations


class FallbackEngine:

    def unsupported_query(
        self,
        query: str
    ) -> dict:

        return {
            "status": "fallback",
            "fallback_used": True,
            "confidence": 0.20,
            "answer": (
                "I could not map this question to a "
                "supported supply-chain analysis. "
                "I can currently analyze supplier risk, "
                "delivery risk, inventory risk, demand "
                "forecasts, anomalies, and supply-chain "
                "summaries."
            ),
            "evidence": [],
            "agents_used": [
                "Fallback Engine"
            ]
        }

    def ambiguous_product_ranking(
        self,
        query: str
    ) -> dict:

        return {
            "status": "fallback",
            "fallback_used": True,
            "confidence": 0.95,
            "answer": (
                "The term 'top product' is ambiguous. "
                "It could refer to highest demand, highest "
                "sales, highest inventory, or highest "
                "inventory risk. Please specify the metric "
                "you want to use."
            ),
            "evidence": [],
            "agents_used": [
                "Query Router",
                "Fallback Engine"
            ],
            "intent": "ambiguous_product_ranking",
            "entity_type": None,
            "entity_id": None,
            "recommendations": [
                "Ask for the product with the highest inventory risk.",
                "Ask for the product with the highest demand.",
                "Ask for the product with the highest stockout rate."
            ],
            "fallback_reason": "ambiguous_product_ranking"
        }

    def missing_entity(
        self,
        intent: str
    ) -> dict:

        examples = {
            "supplier_risk": "S0109",
            "inventory_risk": "P00003",
            "forecast": "P00003"
        }

        example = examples.get(
            intent,
            "a valid entity ID"
        )

        return {
            "status": "fallback",
            "fallback_used": True,
            "confidence": 0.30,
            "answer": (
                f"Please provide the relevant entity ID. "
                f"For example: {example}."
            ),
            "evidence": [],
            "agents_used": [
                "Fallback Engine"
            ]
        }