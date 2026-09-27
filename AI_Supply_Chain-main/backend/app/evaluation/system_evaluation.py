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
import json
from app.models.entities import EvaluationResult
from app.services.data_service import DataService
from app.evaluation.rag_evaluator import RAGEvaluator


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

        self.rag_evaluator = (
            RAGEvaluator()
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

        overall_start = time.perf_counter()
        db = SessionLocal()

        try:
            # 1. Clear previous evaluation results to maintain a clean snapshot
            self.clear_evaluation_results()

            # 2. Run Hybrid RAG Evaluation Suite
            suite_result = self.rag_evaluator.run_suite(db=db)
            self.rag_evaluator.save_results(db=db, results=suite_result["results"])

            # 3. Routing & Forecast evaluation for backward compatibility
            routing = self.evaluate_routing()
            forecast = self.evaluate_forecast(
                product_id=product_id,
                horizon=horizon
            )

            total_latency = (time.perf_counter() - overall_start) * 1000

            # 4. Generate comprehensive summary
            summary = self.get_summary()

            return {
                "status": "success",
                "summary": summary,
                "evaluation": {
                    "routing": routing,
                    "forecast": forecast,
                    "query_quality": {
                        "evidence_grounding_rate": summary.get("grounding_rate", 0.0),
                    },
                    "system": {
                        "total_queries": summary.get("total_evaluations", 0),
                        "successful_queries": summary.get("successful_queries", 0),
                        "fallback_count": int(summary.get("total_evaluations", 0) * summary.get("fallback_rate", 0.0)),
                        "fallback_rate": summary.get("fallback_rate", 0.0),
                        "average_latency_ms": summary.get("average_latency_ms", 0.0),
                    },
                    "evaluation_runtime_ms": round(total_latency, 2),
                },
                "query_results": suite_result["results"],
            }

        finally:
            db.close()

    # =========================================================
    # STORED EVALUATION SUMMARY
    # =========================================================

    def get_summary(self) -> dict[str, Any]:

        db = SessionLocal()

        try:
            records = (
                db.query(EvaluationResult)
                .order_by(EvaluationResult.created_at.desc())
                .all()
            )

            if not records:
                return {
                    "status": "success",
                    "total_evaluations": 0,
                    "total_evaluation_records": 0,
                    "successful_queries": 0,
                    "failed_queries": 0,
                    "success_rate": 0.0,
                    "planner_accuracy": None,
                    "retrieval_accuracy": None,
                    "grounding_rate": None,
                    "evidence_grounding_rate": 0.0,
                    "relevance_rate": 0.0,
                    "rbac_accuracy": None,
                    "fallback_accuracy": None,
                    "audit_completeness": None,
                    "fallback_rate": 0.0,
                    "average_latency_ms": 0.0,
                    "p95_latency_ms": 0.0,
                    "structured_query_count": 0,
                    "semantic_query_count": 0,
                    "hybrid_query_count": 0,
                    "denied_query_count": 0,
                    "llm_used_count": 0,
                    "llm_failure_count": 0,
                    "retrieval_distribution": {
                        "structured": 0,
                        "semantic": 0,
                        "hybrid": 0,
                    },
                    "message": "No evaluation results have been stored yet.",
                }

            total = len(records)
            successful = sum(1 for r in records if (r.success if r.success is not None else r.relevant))
            failed = total - successful

            planner_corr = sum(1 for r in records if r.planner_correct)
            retrieval_corr = sum(1 for r in records if r.retrieval_correct)
            rbac_corr = sum(1 for r in records if r.rbac_correct)
            fallback_corr = sum(1 for r in records if r.fallback_correct)
            audit_comp = sum(1 for r in records if r.audit_complete)

            grounded_scores = [r.grounding_score if r.grounding_score is not None else (1.0 if r.evidence_grounded else 0.0) for r in records]
            relevant_scores = [r.relevance_score if r.relevance_score is not None else (1.0 if r.relevant else 0.0) for r in records]

            fallback_cnt = sum(1 for r in records if r.fallback_used)
            latencies = [r.latency_ms for r in records if r.latency_ms is not None]
            avg_lat = sum(latencies) / len(latencies) if latencies else 0.0
            lat_sorted = sorted(latencies) if latencies else [0.0]
            p95_idx = min(int(0.95 * len(lat_sorted)), len(lat_sorted) - 1)
            p95_lat = lat_sorted[p95_idx]

            struct_cnt = sum(1 for r in records if str(r.retrieval_mode or "").lower() == "structured")
            sem_cnt = sum(1 for r in records if str(r.retrieval_mode or "").lower() == "semantic")
            hyb_cnt = sum(1 for r in records if str(r.retrieval_mode or "").lower() == "hybrid")
            denied_cnt = sum(1 for r in records if str(r.actual_behavior or "").lower().startswith("status=denied") or r.rbac_correct is False)
            llm_cnt = sum(1 for r in records if r.llm_used)
            llm_fail_cnt = sum(1 for r in records if r.llm_used and r.fallback_used)

            grounding_rate = round(sum(grounded_scores) / total, 4)
            relevance_rate = round(sum(relevant_scores) / total, 4)

            return {
                "status": "success",
                "total_evaluations": total,
                "total_evaluation_records": total,
                "successful_queries": successful,
                "failed_queries": failed,
                "success_rate": round(successful / total, 4),
                "planner_accuracy": round(planner_corr / total, 4) if total else None,
                "retrieval_accuracy": round(retrieval_corr / total, 4) if total else None,
                "grounding_rate": grounding_rate,
                "evidence_grounding_rate": grounding_rate,
                "relevance_rate": relevance_rate,
                "rbac_accuracy": round(rbac_corr / total, 4) if total else None,
                "fallback_accuracy": round(fallback_corr / total, 4) if total else None,
                "audit_completeness": round(audit_comp / total, 4) if total else None,
                "fallback_rate": round(fallback_cnt / total, 4),
                "average_latency_ms": round(avg_lat, 2),
                "p95_latency_ms": round(p95_lat, 2),
                "structured_query_count": struct_cnt,
                "semantic_query_count": sem_cnt,
                "hybrid_query_count": hyb_cnt,
                "denied_query_count": denied_cnt,
                "llm_used_count": llm_cnt,
                "llm_failure_count": llm_fail_cnt,
                "retrieval_distribution": {
                    "structured": struct_cnt,
                    "semantic": sem_cnt,
                    "hybrid": hyb_cnt,
                },
            }

        finally:
            db.close()

    # =========================================================
    # STORED DETAILED RESULTS
    # =========================================================

    def get_results(self, limit: int = 50) -> list[dict[str, Any]]:

        db = SessionLocal()

        try:
            records = (
                db.query(EvaluationResult)
                .order_by(EvaluationResult.created_at.desc())
                .limit(limit)
                .all()
            )

            results: list[dict[str, Any]] = []
            for r in records:
                safe_details = {}
                if r.details:
                    try:
                        safe_details = json.loads(r.details)
                    except Exception:
                        safe_details = {}

                # Never expose credentials or tokens
                sanitized_details = {
                    k: v for k, v in safe_details.items()
                    if k not in {"token", "jwt", "password", "authorization", "api_key", "secret"}
                }

                results.append({
                    "id": r.id,
                    "query": r.question,
                    "expected_behavior": r.expected_behavior or r.expected_answer or "N/A",
                    "actual_behavior": r.actual_behavior or (r.actual_answer[:120] if r.actual_answer else "N/A"),
                    "planner_correct": r.planner_correct if r.planner_correct is not None else r.entity_correct,
                    "retrieval_correct": r.retrieval_correct if r.retrieval_correct is not None else r.routing_correct,
                    "grounding_score": r.grounding_score if r.grounding_score is not None else (1.0 if r.evidence_grounded else 0.0),
                    "relevance_score": r.relevance_score if r.relevance_score is not None else (1.0 if r.relevant else 0.0),
                    "rbac_correct": r.rbac_correct if r.rbac_correct is not None else True,
                    "fallback_correct": r.fallback_correct if r.fallback_correct is not None else (not r.fallback_used),
                    "audit_complete": r.audit_complete if r.audit_complete is not None else True,
                    "latency_ms": round(r.latency_ms, 2) if r.latency_ms is not None else 0.0,
                    "retrieval_mode": r.retrieval_mode or "structured",
                    "evidence_count": r.evidence_count or 0,
                    "llm_used": bool(r.llm_used),
                    "fallback_used": bool(r.fallback_used),
                    "success": bool(r.success if r.success is not None else r.answer_correct),
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "details": sanitized_details,
                })

            return results

        finally:
            db.close()
            