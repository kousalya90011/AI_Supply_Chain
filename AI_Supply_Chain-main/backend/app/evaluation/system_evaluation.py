from __future__ import annotations

import time
from typing import Any

from app.agents.graph import SupplyChainGraph
from app.evaluation.forecast_evaluation import ForecastEvaluator
from app.evaluation.grounding_evaluation import (
    EvidenceGroundingEvaluator
)
from app.evaluation.query_evaluation import (
    QueryEvaluationEngine
)
from app.models.database import SessionLocal
from app.models.entities import EvaluationResult
from app.services.data_service import DataService


class SystemEvaluationEngine:

    def __init__(self):

        self.data_service = DataService()

        self.routing_evaluator = (
            QueryEvaluationEngine()
        )

        self.forecast_evaluator = (
            ForecastEvaluator()
        )

        self.graph = SupplyChainGraph()

        self.grounding_evaluator = (
            EvidenceGroundingEvaluator()
        )

    # =========================================================
    # ROUTING EVALUATION
    # =========================================================

    def evaluate_routing(self) -> dict[str, Any]:

        result = (
            self.routing_evaluator
            .evaluate_routing()
        )

        return {
            "intent_accuracy": result[
                "intent_accuracy"
            ],
            "entity_type_accuracy": result[
                "entity_type_accuracy"
            ],
            "entity_id_accuracy": result[
                "entity_id_accuracy"
            ],
            "total_queries": result[
                "total_queries"
            ]
        }

    # =========================================================
    # FORECAST EVALUATION
    # =========================================================

    def evaluate_forecast(
        self,
        product_id: str = "P00003",
        horizon: int = 7
    ) -> dict[str, Any]:

        datasets = (
            self.data_service
            .load_data()["datasets"]
        )

        evaluation = (
            self.forecast_evaluator
            .evaluate_product(
                demand_df=datasets["demand"],
                product_id=product_id,
                horizon=horizon
            )
        )

        if evaluation["status"] != "success":
            return evaluation

        return {
            "product_id": product_id,
            "horizon": horizon,
            "mae": evaluation[
                "metrics"
            ]["mae"],
            "rmse": evaluation[
                "metrics"
            ]["rmse"],
            "mape": evaluation[
                "metrics"
            ]["mape"]
        }

    # =========================================================
    # QUERY EVALUATION
    # =========================================================

    def evaluate_queries(self) -> dict[str, Any]:

        benchmarks = (
            self.routing_evaluator
            .load_benchmarks()
        )

        results = []

        successful = 0
        fallback_count = 0
        grounded_count = 0

        total_latency = 0.0

        for benchmark in benchmarks:

            query = benchmark["query"]

            start = time.perf_counter()

            try:

                response = self.graph.run(
                    query
                )

                latency = response.get(
                    "latency_ms",
                    (
                        time.perf_counter()
                        - start
                    ) * 1000
                )

                status = response.get(
                    "status",
                    "unknown"
                )

                fallback_used = response.get(
                    "fallback_used",
                    False
                )

                evidence = response.get(
                    "evidence",
                    []
                )

                answer = response.get(
                    "answer",
                    ""
                )

                if status == "success":
                    successful += 1

                if fallback_used:
                    fallback_count += 1

                expected_intent = (
                    benchmark[
                        "expected_intent"
                    ]
                )

                # Unsupported benchmark queries
                # are intentionally considered grounded
                # because there is no evidence requirement.
                if expected_intent == "unknown":

                    grounded = True

                    grounding_result = {
                        "grounded": True,
                        "coverage": 1.0,
                        "checked_fields": [],
                        "matched_fields": [],
                        "missing_fields": []
                    }

                else:

                    grounding_result = (
                        self.grounding_evaluator
                        .evaluate(
                            answer=answer,
                            evidence=evidence
                        )
                    )

                    grounded = (
                        grounding_result[
                            "grounded"
                        ]
                    )

                if grounded:
                    grounded_count += 1

                total_latency += float(
                    latency
                )

                results.append({
                    "query": query,
                    "status": status,
                    "fallback_used": (
                        fallback_used
                    ),
                    "latency_ms": round(
                        float(latency),
                        2
                    ),
                    "evidence_available": bool(
                        evidence
                    ),
                    "answer_available": bool(
                        answer.strip()
                    ),
                    "grounded": grounded,
                    "grounding_coverage": (
                        grounding_result[
                            "coverage"
                        ]
                    ),
                    "matched_fields": (
                        grounding_result[
                            "matched_fields"
                        ]
                    ),
                    "missing_fields": (
                        grounding_result[
                            "missing_fields"
                        ]
                    )
                })

            except Exception as exc:

                latency = (
                    time.perf_counter()
                    - start
                ) * 1000

                fallback_count += 1

                total_latency += latency

                results.append({
                    "query": query,
                    "status": "error",
                    "fallback_used": True,
                    "latency_ms": round(
                        latency,
                        2
                    ),
                    "evidence_available": False,
                    "answer_available": False,
                    "grounded": False,
                    "grounding_coverage": 0.0,
                    "matched_fields": [],
                    "missing_fields": [],
                    "error": str(exc)
                })

        total = len(benchmarks)

        return {
            "total_queries": total,

            "successful_queries": successful,

            "fallback_count": fallback_count,

            "fallback_rate": round(
                fallback_count / total,
                4
            ) if total else 0.0,

            "evidence_grounding_rate": round(
                grounded_count / total,
                4
            ) if total else 0.0,

            "average_latency_ms": round(
                total_latency / total,
                2
            ) if total else 0.0,

            "results": results
        }

    # =========================================================
    # SAVE EVALUATION RESULTS
    # =========================================================

    def save_query_results(
        self,
        query_results: list[dict[str, Any]]
    ) -> None:

        db = SessionLocal()

        try:

            for result in query_results:

                evaluation = EvaluationResult(

                    question=result.get(
                        "query"
                    ),

                    expected_answer=None,

                    actual_answer=result.get(
                        "answer"
                    ),

                    answer_correct=None,

                    entity_correct=None,

                    evidence_grounded=result.get(
                        "grounded",
                        False
                    ),

                    relevant=(
                        result.get(
                            "status"
                        ) == "success"
                    ),

                    routing_correct=None,

                    latency_ms=result.get(
                        "latency_ms",
                        0.0
                    )
                )

                db.add(evaluation)

            db.commit()

        except Exception:

            db.rollback()

            raise

        finally:

            db.close()

    # =========================================================
    # CLEAR PREVIOUS EVALUATION RESULTS
    # =========================================================

    def clear_evaluation_results(self) -> None:

        db = SessionLocal()

        try:

            db.query(
                EvaluationResult
            ).delete()

            db.commit()

        except Exception:

            db.rollback()

            raise

        finally:

            db.close()

    # =========================================================
    # COMPLETE SYSTEM EVALUATION
    # =========================================================

    def run_full_evaluation(
        self,
        product_id: str = "P00003",
        horizon: int = 7
    ) -> dict[str, Any]:

        overall_start = (
            time.perf_counter()
        )

        # -----------------------------------------------------
        # Start from a clean evaluation snapshot.
        #
        # This prevents old runs from contaminating
        # the current evaluation summary.
        # -----------------------------------------------------

        self.clear_evaluation_results()

        routing = (
            self.evaluate_routing()
        )

        forecast = (
            self.evaluate_forecast(
                product_id=product_id,
                horizon=horizon
            )
        )

        queries = (
            self.evaluate_queries()
        )

        # -----------------------------------------------------
        # Persist only this evaluation run
        # -----------------------------------------------------

        self.save_query_results(
            queries["results"]
        )

        total_latency = (
            time.perf_counter()
            - overall_start
        ) * 1000

        return {

            "status": "success",

            "evaluation": {

                "routing": routing,

                "forecast": forecast,

                "query_quality": {

                    "evidence_grounding_rate":
                        queries[
                            "evidence_grounding_rate"
                        ]
                },

                "system": {

                    "total_queries":
                        queries[
                            "total_queries"
                        ],

                    "successful_queries":
                        queries[
                            "successful_queries"
                        ],

                    "fallback_count":
                        queries[
                            "fallback_count"
                        ],

                    "fallback_rate":
                        queries[
                            "fallback_rate"
                        ],

                    "average_latency_ms":
                        queries[
                            "average_latency_ms"
                        ]
                },

                "evaluation_runtime_ms":
                    round(
                        total_latency,
                        2
                    )
            },

            "query_results":
                queries["results"]
        }

    # =========================================================
    # STORED EVALUATION SUMMARY
    # =========================================================

    def get_summary(
        self
    ) -> dict[str, Any]:

        db = SessionLocal()

        try:

            records = (
                db.query(
                    EvaluationResult
                )
                .order_by(
                    EvaluationResult.created_at.desc()
                )
                .all()
            )

            if not records:

                return {
                    "status": "success",
                    "total_evaluation_records": 0,
                    "evidence_grounding_rate": 0.0,
                    "relevance_rate": 0.0,
                    "fallback_rate": 0.0,
                    "average_latency_ms": 0.0,
                    "message": (
                        "No evaluation results "
                        "have been stored yet."
                    )
                }

            total = len(records)

            grounded = sum(
                1
                for record in records
                if record.evidence_grounded
            )

            relevant = sum(
                1
                for record in records
                if record.relevant
            )

            fallback_like = sum(
                1
                for record in records
                if not record.relevant
            )

            latencies = [
                record.latency_ms
                for record in records
                if record.latency_ms is not None
            ]

            average_latency = (
                sum(latencies)
                / len(latencies)
                if latencies
                else 0.0
            )

            return {

                "status": "success",

                "total_evaluation_records":
                    total,

                "evidence_grounding_rate":
                    round(
                        grounded / total,
                        4
                    ),

                "relevance_rate":
                    round(
                        relevant / total,
                        4
                    ),

                "fallback_rate":
                    round(
                        fallback_like / total,
                        4
                    ),

                "average_latency_ms":
                    round(
                        average_latency,
                        2
                    )
            }

        finally:

            db.close()
            