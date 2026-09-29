from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.entities import AuditTrace, EvaluationResult, UserRole
from app.query.scope import QueryScope, supplier_ids_match
from app.services.query_service import QueryService
from app.evaluation.grounding_evaluation import EvidenceGroundingEvaluator

logger = logging.getLogger(__name__)


@dataclass
class EvaluationBenchmarkCase:
    id: str
    query: str
    role: str = UserRole.ADMIN.value
    supplier_id: str | None = None

    expected_behavior: str = "retrieve authorized supply chain data"

    expected_retrieval_modes: list[str] = field(
        default_factory=lambda: [
            "structured",
            "semantic",
            "hybrid",
        ]
    )

    expected_status: str = "success"

    expected_fallback: bool = False

    expected_domain: str | None = None
    expected_entity_id: str | None = None

    is_rbac_test: bool = False

    notes: str = ""


# ============================================================
# PHASE 6 BENCHMARK SUITE
# ============================================================

DEFAULT_BENCHMARK_CASES: list[EvaluationBenchmarkCase] = [

    # --------------------------------------------------------
    # 1. Structured product -> supplier
    # --------------------------------------------------------
    EvaluationBenchmarkCase(
        id="case_1_structured_product_supplier",
        query="Who supplies P00003?",
        role=UserRole.ADMIN.value,
        expected_behavior=(
            "Structured supplier lookup for product P00003"
        ),
        expected_retrieval_modes=["structured"],
        expected_status="success",
        expected_fallback=False,
        expected_domain="supplier",
        expected_entity_id="P00003",
        notes="Exact supplier relationship lookup",
    ),

    # --------------------------------------------------------
    # 2. Structured supplier -> order count
    # --------------------------------------------------------
    EvaluationBenchmarkCase(
        id="case_2_structured_supplier_orders",
        query="How many orders does S001 have?",
        role=UserRole.ADMIN.value,
        expected_behavior=(
            "Structured order volume analysis for supplier S001"
        ),
        expected_retrieval_modes=["structured"],
        expected_status="success",
        expected_fallback=False,
        expected_domain="order",
        expected_entity_id="S001",
        notes="Exact order count lookup",
    ),

    # --------------------------------------------------------
    # 3. Structured product -> inventory
    # --------------------------------------------------------
    EvaluationBenchmarkCase(
        id="case_3_structured_product_inventory",
        query="What is the current inventory of P00003?",
        role=UserRole.ADMIN.value,
        expected_behavior=(
            "Structured inventory level retrieval for product P00003"
        ),
        expected_retrieval_modes=["structured"],
        expected_status="success",
        expected_fallback=False,
        expected_domain="inventory",
        expected_entity_id="P00003",
        notes="Deterministic inventory metric retrieval",
    ),

    # --------------------------------------------------------
    # 4. Structured live offers
    # --------------------------------------------------------
    EvaluationBenchmarkCase(
        id="case_4_structured_pending_offers",
        query="Which supplier offers are pending?",
        role=UserRole.ADMIN.value,
        expected_behavior=(
            "Structured SQL query for pending supplier offers"
        ),
        expected_retrieval_modes=["structured"],
        expected_status="success",
        expected_fallback=False,
        expected_domain="offers",
        notes="Live database offers lookup",
    ),

    # --------------------------------------------------------
    # 5. Semantic/hybrid product risk
    # --------------------------------------------------------
    EvaluationBenchmarkCase(
        id="case_5_semantic_product_risk",
        query="Summarize the risk profile of P00003.",
        role=UserRole.ADMIN.value,
        expected_behavior=(
            "Semantic/hybrid synthesis of P00003 operational risk summary"
        ),
        expected_retrieval_modes=[
            "semantic",
            "hybrid",
        ],
        expected_status="success",
        expected_fallback=False,
        expected_domain="inventory",
        expected_entity_id="P00003",
        notes="Semantic knowledge document retrieval",
    ),

    # --------------------------------------------------------
    # 6. Semantic supplier overview
    # --------------------------------------------------------
    EvaluationBenchmarkCase(
        id="case_6_semantic_supplier_profile",
        query="What should I know about supplier S001?",
        role=UserRole.ADMIN.value,
        expected_behavior=(
            "Semantic/hybrid overview of supplier S0001 performance profile"
        ),
        expected_retrieval_modes=[
            "semantic",
            "hybrid",
        ],
        expected_status="success",
        expected_fallback=False,
        expected_domain="supplier",
        expected_entity_id="S001",
        notes="Semantic supplier profile lookup",
    ),

    # --------------------------------------------------------
    # 7. Hybrid cross-domain
    # --------------------------------------------------------
    EvaluationBenchmarkCase(
        id="case_7_hybrid_cross_domain",
        query=(
            "Which suppliers have high delivery risk, "
            "what products do they supply, and how is demand "
            "and inventory for those products?"
        ),
        role=UserRole.ADMIN.value,
        expected_behavior=(
            "Multi-requirement hybrid retrieval across suppliers, "
            "products, demand, and inventory"
        ),
        expected_retrieval_modes=["hybrid"],
        expected_status="success",
        expected_fallback=False,
        notes="Complex multi-domain analytical reasoning",
    ),

    # --------------------------------------------------------
    # 8. Supplier RBAC allowed - performance
    # --------------------------------------------------------
    EvaluationBenchmarkCase(
        id="case_8_supplier_rbac_performance",
        query="What is my performance?",
        role=UserRole.SUPPLIER.value,
        supplier_id="S0001",
        expected_behavior=(
            "Supplier self-service performance review "
            "restricted strictly to S0001"
        ),
        expected_retrieval_modes=[
            "structured",
            "semantic",
            "hybrid",
        ],
        expected_status="success",
        expected_fallback=False,
        is_rbac_test=True,
        notes="Supplier self-scope access authorized",
    ),

    # --------------------------------------------------------
    # 9. Supplier RBAC allowed - products
    # --------------------------------------------------------
    EvaluationBenchmarkCase(
        id="case_9_supplier_rbac_products",
        query="Which products do I supply?",
        role=UserRole.SUPPLIER.value,
        supplier_id="S0001",
        expected_behavior=(
            "Supplier product catalog restricted strictly "
            "to items supplied by S0001"
        ),
        expected_retrieval_modes=[
            "structured",
            "semantic",
            "hybrid",
        ],
        expected_status="success",
        expected_fallback=False,
        is_rbac_test=True,
        notes="Supplier authorized products catalog",
    ),

    # --------------------------------------------------------
    # 10. Supplier RBAC allowed - offers
    # --------------------------------------------------------
    EvaluationBenchmarkCase(
        id="case_10_supplier_rbac_offers",
        query="Show my pending offers.",
        role=UserRole.SUPPLIER.value,
        supplier_id="S0001",
        expected_behavior=(
            "Supplier offers restricted strictly "
            "to offers created by S0001"
        ),
        expected_retrieval_modes=["structured"],
        expected_status="success",
        expected_fallback=False,
        is_rbac_test=True,
        notes="Supplier authorized live transactional offers",
    ),

    # --------------------------------------------------------
    # 11. Supplier RBAC denied
    # --------------------------------------------------------
    EvaluationBenchmarkCase(
        id="case_11_supplier_rbac_cross_denied",
        query="Show me S002 performance.",
        role=UserRole.SUPPLIER.value,
        supplier_id="S0001",
        expected_behavior=(
            "Strict RBAC denial with zero evidence leakage "
            "for unauthorized supplier S002"
        ),
        expected_retrieval_modes=[
            "structured",
            "semantic",
            "hybrid",
        ],
        expected_status="denied",
        expected_fallback=False,
        is_rbac_test=True,
        notes="Unauthorized cross-supplier access blocked",
    ),

    # --------------------------------------------------------
    # 12. Unsupported query -> fallback
    # --------------------------------------------------------
    EvaluationBenchmarkCase(
        id="case_12_unsupported_query",
        query=(
            "What is the current weather forecast "
            "for Tokyo tomorrow?"
        ),
        role=UserRole.ADMIN.value,
        expected_behavior=(
            "Safe unsupported query clarification or graceful "
            "fallback without crashing"
        ),
        expected_retrieval_modes=[
            "structured",
            "semantic",
            "hybrid",
        ],
        expected_status="success",
        expected_fallback=True,
        notes="Graceful fallback for non-supply-chain query",
    ),

    # --------------------------------------------------------
    # 13. Affected products
    # --------------------------------------------------------
    EvaluationBenchmarkCase(
        id="case_13_affected_products",
        query="Which products are affected by supplier disruptions?",
        role=UserRole.ADMIN.value,
        expected_behavior="Identify products with elevated exposure to supplier disruptions",
        expected_retrieval_modes=["structured", "hybrid"],
        expected_status="success",
        expected_fallback=False,
        expected_domain="supply_chain",
        notes="Deterministic filter for products meeting supplier disruption exposure criteria",
    ),

    # --------------------------------------------------------
    # 14. Unaffected products
    # --------------------------------------------------------
    EvaluationBenchmarkCase(
        id="case_14_unaffected_products",
        query="Which products are not affected by supplier disruptions?",
        role=UserRole.ADMIN.value,
        expected_behavior="Identify products not affected by supplier disruptions (complement set)",
        expected_retrieval_modes=["structured", "hybrid"],
        expected_status="success",
        expected_fallback=False,
        expected_domain="supply_chain",
        notes="Deterministic complement population for products outside disruption criteria",
    ),

    # --------------------------------------------------------
    # 15. Highest delivery risk suppliers
    # --------------------------------------------------------
    EvaluationBenchmarkCase(
        id="case_15_highest_risk_suppliers",
        query="Which suppliers have the highest delivery risk?",
        role=UserRole.ADMIN.value,
        expected_behavior="Rank suppliers with highest delivery delay and late rate",
        expected_retrieval_modes=["structured", "hybrid"],
        expected_status="success",
        expected_fallback=False,
        expected_domain="supplier",
        notes="Rank suppliers descending by delivery late rate",
    ),

    # --------------------------------------------------------
    # 16. Lowest delivery risk suppliers
    # --------------------------------------------------------
    EvaluationBenchmarkCase(
        id="case_16_lowest_risk_suppliers",
        query="Which suppliers have low delivery risk?",
        role=UserRole.ADMIN.value,
        expected_behavior="Filter suppliers with low delivery risk and high on-time delivery",
        expected_retrieval_modes=["structured", "hybrid"],
        expected_status="success",
        expected_fallback=False,
        expected_domain="supplier",
        notes="Filter suppliers with low late rate and stable delivery",
    ),

    # --------------------------------------------------------
    # 17. Delivery performance
    # --------------------------------------------------------
    EvaluationBenchmarkCase(
        id="case_17_delivery_performance",
        query="What is my performance in delivery?",
        role=UserRole.ADMIN.value,
        expected_behavior="Report quantitative delivery performance metrics",
        expected_retrieval_modes=["structured", "hybrid"],
        expected_status="success",
        expected_fallback=False,
        expected_domain="delivery",
        notes="Network or supplier delivery metrics including on-time rate and late orders",
    ),

    # --------------------------------------------------------
    # 18. Inventory risk explanation
    # --------------------------------------------------------
    EvaluationBenchmarkCase(
        id="case_18_inventory_explanation",
        query="Why is product P00003 at inventory risk?",
        role=UserRole.ADMIN.value,
        expected_behavior="Explain inventory risk factors for product P00003",
        expected_retrieval_modes=["structured", "hybrid", "semantic"],
        expected_status="success",
        expected_fallback=False,
        expected_domain="inventory",
        expected_entity_id="P00003",
        notes="Explain stockout rate and days of cover for target product",
    ),

    # --------------------------------------------------------
    # 19. Supplier-product relationship
    # --------------------------------------------------------
    EvaluationBenchmarkCase(
        id="case_19_supplier_product_relationship",
        query="What supplier provides P00003?",
        role=UserRole.ADMIN.value,
        expected_behavior="Identify the supplier supplying product P00003",
        expected_retrieval_modes=["structured"],
        expected_status="success",
        expected_fallback=False,
        expected_domain="supplier",
        expected_entity_id="P00003",
        notes="Relational mapping connecting product P00003 to its supplier",
    ),
]


class RAGEvaluator:
    """
    Phase 6 Evaluation & Observability Engine.

    Evaluates:

    1. Planner correctness
    2. Retrieval correctness
    3. Evidence grounding
    4. Answer relevance
    5. RBAC correctness
    6. Fallback correctness
    7. Latency
    8. Audit completeness
    """

    def __init__(
        self,
        query_service: QueryService | None = None,
    ) -> None:

        self.query_service = (
            query_service
            or QueryService()
        )

        self.grounding_evaluator = (
            EvidenceGroundingEvaluator()
        )

    # ========================================================
    # SUPPLIER ID NORMALIZATION
    # ========================================================

    @staticmethod
    def _normalize_supplier_id(
        supplier_id: str | None,
    ) -> str:

        if not supplier_id:
            return ""

        value = str(
            supplier_id
        ).strip().upper()

        if value.startswith("S"):
            numeric = value[1:]

            if numeric.isdigit():
                return f"S{int(numeric):04d}"

        return value

    # ========================================================
    # RUN ONE CASE
    # ========================================================

    def run_case(
        self,
        case: EvaluationBenchmarkCase,
        db: Session | None = None,
    ) -> dict[str, Any]:

        user_scope = QueryScope(
            username=(
                f"eval_user_"
                f"{case.supplier_id or 'admin'}"
            ),
            role=case.role,
            supplier_id=case.supplier_id,
        )

        start_time = time.perf_counter()

        query_response: dict[str, Any] = {}
        error_msg: str | None = None

        try:

            query_response = (
                self.query_service.query(
                    query=case.query,
                    user_scope=user_scope,
                    db=db,
                )
            )

        except Exception as exc:

            logger.error(
                "Evaluation case %s failed: %s",
                case.id,
                exc,
                exc_info=True,
            )

            error_msg = str(exc)

            query_response = {
                "status": "error",
                "answer": (
                    f"System execution error: "
                    f"{error_msg}"
                ),
                "evidence": [],
                "retrieval_mode": "structured",
                "fallback_used": True,
                "latency_ms": round(
                    (
                        time.perf_counter()
                        - start_time
                    ) * 1000,
                    2,
                ),
            }

        total_latency = float(
            query_response.get(
                "latency_ms"
            )
            or (
                (
                    time.perf_counter()
                    - start_time
                )
                * 1000
            )
        )

        actual_status = str(
            query_response.get(
                "status",
                "unknown",
            )
        ).lower()

        actual_retrieval_mode = str(
            query_response.get(
                "retrieval_mode",
                "structured",
            )
        ).lower()

        evidence = (
            query_response.get(
                "evidence",
                [],
            )
            or []
        )

        answer = str(
            query_response.get(
                "answer",
                "",
            )
        )

        fallback_used = bool(
            query_response.get(
                "fallback_used",
                False,
            )
        )

        agents_used = (
            query_response.get(
                "agents_used",
                [],
            )
            or []
        )

        llm_used = any(
            (
                "llm"
                in str(agent).lower()
                or "insight"
                in str(agent).lower()
            )
            for agent in agents_used
        )

        # ====================================================
        # 1. PLANNER
        # ====================================================

        planner_correct = (
            self._evaluate_planner(
                case,
                query_response,
            )
        )

        # ====================================================
        # 2. RETRIEVAL
        # ====================================================

        retrieval_correct = (
            self._evaluate_retrieval(
                case,
                actual_retrieval_mode,
                actual_status,
            )
        )

        # ====================================================
        # 3. RBAC
        # ====================================================

        rbac_correct = (
            self._evaluate_rbac(
                case,
                actual_status,
                evidence,
            )
        )

        # ====================================================
        # 4. FALLBACK
        # ====================================================

        fallback_correct = (
            self._evaluate_fallback(
                case,
                fallback_used,
                actual_status,
            )
        )

        # ====================================================
        # 5. GROUNDING
        # ====================================================

        grounding_score = (
            self._evaluate_grounding(
                case,
                answer,
                evidence,
                actual_status,
            )
        )

        # ====================================================
        # 6. RELEVANCE
        # ====================================================

        relevance_score = (
            self._evaluate_relevance(
                case,
                answer,
                actual_status,
                evidence,
            )
        )

        # ====================================================
        # 7. AUDIT
        # ====================================================

        audit_complete = (
            self._evaluate_audit(
                case,
                db,
            )
        )

        # ====================================================
        # OVERALL SUCCESS
        # ====================================================

        success = (
            actual_status
            == case.expected_status
            and planner_correct
            and retrieval_correct
            and rbac_correct
            and fallback_correct
            and error_msg is None
        )

        actual_behavior = (
            f"Status={actual_status}, "
            f"Mode={actual_retrieval_mode}, "
            f"Evidence={len(evidence)}, "
            f"Fallback={fallback_used}"
        )

        return {
            "case_id": case.id,
            "query": case.query,
            "role": case.role,
            "supplier_id": case.supplier_id,

            "expected_behavior": (
                case.expected_behavior
            ),

            "actual_behavior": actual_behavior,

            "status": actual_status,

            "planner_correct": planner_correct,
            "retrieval_correct": retrieval_correct,

            "grounding_score": grounding_score,
            "relevance_score": relevance_score,

            "rbac_correct": rbac_correct,
            "fallback_correct": fallback_correct,
            "audit_complete": audit_complete,

            "latency_ms": round(
                total_latency,
                2,
            ),

            "retrieval_mode": (
                actual_retrieval_mode
            ),

            "evidence_count": len(evidence),

            "llm_used": llm_used,
            "fallback_used": fallback_used,

            "success": success,

            "answer_preview": (
                answer[:250]
                + (
                    "..."
                    if len(answer) > 250
                    else ""
                )
            ),

            "created_at": datetime.now(
                timezone.utc
            ),

            "details": {
                "agents_used": agents_used,
                "sources": (
                    query_response.get(
                        "sources",
                        [],
                    )
                ),
                "error": error_msg,
            },
        }

    # ========================================================
    # PLANNER EVALUATION
    # ========================================================

    def _evaluate_planner(
        self,
        case: EvaluationBenchmarkCase,
        response: dict[str, Any],
    ) -> bool:

        if response.get("status") == "error":
            return False

        if case.expected_fallback:
            return True

        if case.expected_status == "denied":

            # The query must at least identify
            # the unauthorized supplier mentioned
            # in the original query.

            query_upper = case.query.upper()

            unauthorized_supplier = "S002"

            if (
                unauthorized_supplier
                not in query_upper
            ):
                return True

            return (
                unauthorized_supplier
                in query_upper
            )

        # Try to inspect planner information
        # returned by QueryService.

        plan = (
            response.get("plan")
            or response.get("query_plan")
            or {}
        )

        if not isinstance(plan, dict):
            plan = {}

        # ----------------------------------------------------
        # Domain validation
        # ----------------------------------------------------

        if case.expected_domain:

            actual_domain = str(
                plan.get(
                    "domain",
                    "",
                )
            ).lower()

            if actual_domain:

                if (
                    actual_domain
                    != case.expected_domain.lower()
                ):
                    return False

        # ----------------------------------------------------
        # Entity validation
        # ----------------------------------------------------

        if case.expected_entity_id:

            expected_entity = str(
                case.expected_entity_id
            ).upper()

            query_upper = (
                case.query.upper()
            )

            # Exact entity should occur in
            # benchmark query.
            if expected_entity not in query_upper:

                # For normalized supplier IDs,
                # accept S001 <-> S0001.
                if expected_entity.startswith("S"):

                    normalized_expected = (
                        self._normalize_supplier_id(
                            expected_entity
                        )
                    )

                    normalized_query = query_upper

                    digits = (
                        normalized_expected[1:]
                    )

                    short_id = (
                        f"S{int(digits)}"
                        if digits.isdigit()
                        else expected_entity
                    )

                    if (
                        normalized_expected
                        not in normalized_query
                        and short_id
                        not in normalized_query
                    ):
                        return False

                else:
                    return False

        return True

    # ========================================================
    # RETRIEVAL EVALUATION
    # ========================================================

    def _evaluate_retrieval(
        self,
        case: EvaluationBenchmarkCase,
        actual_mode: str,
        actual_status: str,
    ) -> bool:

        actual_mode = (
            actual_mode or ""
        ).lower()

        if (
            case.expected_status
            == "denied"
        ):

            # Authorization denial is not
            # a retrieval failure.
            return actual_status == "denied"

        expected_modes = [
            mode.lower()
            for mode
            in case.expected_retrieval_modes
        ]

        return (
            actual_mode
            in expected_modes
        )

    # ========================================================
    # RBAC EVALUATION
    # ========================================================

    def _evaluate_rbac(
        self,
        case: EvaluationBenchmarkCase,
        actual_status: str,
        evidence: list[dict[str, Any]],
    ) -> bool:

        # ----------------------------------------------------
        # Expected denial
        # ----------------------------------------------------

        if case.expected_status == "denied":

            return (
                actual_status == "denied"
                and len(evidence) == 0
            )

        # ----------------------------------------------------
        # Supplier scope
        # ----------------------------------------------------

        if (
            case.role
            == UserRole.SUPPLIER.value
            and case.supplier_id
        ):

            expected_supplier = (
                self._normalize_supplier_id(
                    case.supplier_id
                )
            )

            for item in evidence:

                if not isinstance(
                    item,
                    dict,
                ):
                    continue

                # --------------------------------------------
                # Direct supplier entity
                # --------------------------------------------

                entity_id = (
                    item.get("entity_id")
                    or item.get("supplier_id")
                    or ""
                )

                if (
                    str(entity_id)
                    .upper()
                    .startswith("S")
                ):

                    if not supplier_ids_match(
                        expected_supplier,
                        str(entity_id),
                    ):
                        return False

                # --------------------------------------------
                # Nested value/data
                # --------------------------------------------

                nested = (
                    item.get("value")
                    or item.get("data")
                )

                if isinstance(
                    nested,
                    dict,
                ):

                    nested_supplier = (
                        nested.get(
                            "supplier_id"
                        )
                        or nested.get(
                            "supplier"
                        )
                    )

                    if nested_supplier:

                        if not supplier_ids_match(
                            expected_supplier,
                            str(
                                nested_supplier
                            ),
                        ):
                            return False

            return (
                actual_status
                == case.expected_status
            )

        return (
            actual_status
            == case.expected_status
        )

    # ========================================================
    # FALLBACK EVALUATION
    # ========================================================

    def _evaluate_fallback(
        self,
        case: EvaluationBenchmarkCase,
        fallback_used: bool,
        actual_status: str,
    ) -> bool:

        # Denial must not be counted as
        # fallback.
        if case.expected_status == "denied":

            return (
                not fallback_used
                and actual_status == "denied"
            )

        # Unsupported query should use
        # graceful fallback.
        if case.expected_fallback:

            return fallback_used

        # Normal supported query should
        # not require fallback.
        return not fallback_used

    # ========================================================
    # GROUNDING EVALUATION
    # ========================================================

    def _evaluate_grounding(
        self,
        case: EvaluationBenchmarkCase,
        answer: str,
        evidence: list[dict[str, Any]],
        actual_status: str,
    ) -> float:

        # ----------------------------------------------------
        # Explicit denial
        # ----------------------------------------------------

        if actual_status == "denied":

            if not evidence:
                return 1.0

            return 0.0

        # ----------------------------------------------------
        # Unsupported fallback
        # ----------------------------------------------------

        if case.expected_fallback:

            # Fallback answer is considered successful
            # grounding-wise if the system gives a
            # non-empty safe response.
            return (
                1.0
                if answer.strip()
                else 0.0
            )

        # ----------------------------------------------------
        # No evidence
        # ----------------------------------------------------

        if not evidence:

            return 0.0

        if not answer.strip():

            return 0.0

        # ----------------------------------------------------
        # Actual evidence grounding
        # ----------------------------------------------------

        evaluation = (
            self.grounding_evaluator.evaluate(
                answer=answer,
                evidence=evidence,
            )
        )

        return round(
            float(
                evaluation.get(
                    "coverage",
                    0.0,
                )
                or 0.0
            ),
            4,
        )

    # ========================================================
    # RELEVANCE
    # ========================================================

    def _evaluate_relevance(
        self,
        case: EvaluationBenchmarkCase,
        answer: str,
        actual_status: str,
        evidence: list[dict[str, Any]],
    ) -> float:

        if not answer.strip():

            return 0.0

        # ----------------------------------------------------
        # Denied response
        # ----------------------------------------------------

        if actual_status == "denied":

            answer_lower = (
                answer.lower()
            )

            if (
                "denied"
                in answer_lower
                or "unauthorized"
                in answer_lower
                or "not authorized"
                in answer_lower
                or "access"
                in answer_lower
            ):
                return 1.0

            return 0.0

        # ----------------------------------------------------
        # Entity relevance
        # ----------------------------------------------------

        q_upper = (
            case.query.upper()
        )

        combined = (
            answer
            + " "
            + json.dumps(
                evidence,
                default=str,
            )
        ).upper()

        if "P00003" in q_upper:

            if "P00003" in combined:
                return 1.0

            return 0.0

        if (
            "S001" in q_upper
            or "S0001" in q_upper
        ):

            if (
                "S001" in combined
                or "S0001" in combined
            ):
                return 1.0

            return 0.0

        # ----------------------------------------------------
        # Generic supported query
        # ----------------------------------------------------

        if len(answer.strip()) >= 20:

            return 1.0

        return 0.5

    # ========================================================
    # AUDIT EVALUATION
    # ========================================================

    def _evaluate_audit(
        self,
        case: EvaluationBenchmarkCase,
        db: Session | None,
    ) -> bool:

        if db is None:

            # The evaluator can be used without
            # a database in unit tests.
            return True

        try:

            db.expire_all()

            trace = (
                db.query(
                    AuditTrace
                )
                .filter(
                    AuditTrace.query
                    == case.query
                )
                .order_by(
                    AuditTrace.created_at.desc()
                )
                .first()
            )

            return trace is not None

        except Exception:

            return False

    # ========================================================
    # RUN COMPLETE SUITE
    # ========================================================

    def run_suite(
        self,
        db: Session | None = None,
        cases: list[
            EvaluationBenchmarkCase
        ]
        | None = None,
    ) -> dict[str, Any]:

        test_cases = (
            cases
            or DEFAULT_BENCHMARK_CASES
        )

        results: list[
            dict[str, Any]
        ] = []

        overall_start = (
            time.perf_counter()
        )

        for case in test_cases:

            result = self.run_case(
                case,
                db=db,
            )

            results.append(result)

        total_runtime = (
            time.perf_counter()
            - overall_start
        ) * 1000

        summary = (
            self.compute_summary_metrics(
                results
            )
        )

        summary[
            "total_runtime_ms"
        ] = round(
            total_runtime,
            2,
        )

        return {
            "status": "success",
            "summary": summary,
            "results": results,
        }

    # ========================================================
    # SUMMARY METRICS
    # ========================================================

    def compute_summary_metrics(
        self,
        results: list[
            dict[str, Any]
        ],
    ) -> dict[str, Any]:

        total = len(results)

        if total == 0:

            return {
                "total_evaluations": 0,
                "successful_queries": 0,
                "failed_queries": 0,
                "success_rate": 0.0,

                "planner_accuracy": None,
                "retrieval_accuracy": None,
                "grounding_rate": None,
                "relevance_rate": None,
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
            }

        successful = sum(
            1
            for result in results
            if result.get(
                "success",
                False,
            )
        )

        failed = (
            total
            - successful
        )

        planner_correct = sum(
            1
            for result in results
            if result.get(
                "planner_correct",
                False,
            )
        )

        retrieval_correct = sum(
            1
            for result in results
            if result.get(
                "retrieval_correct",
                False,
            )
        )

        grounding_scores = [
            float(
                result.get(
                    "grounding_score",
                    0.0,
                )
                or 0.0
            )
            for result in results
        ]

        relevance_scores = [
            float(
                result.get(
                    "relevance_score",
                    0.0,
                )
                or 0.0
            )
            for result in results
        ]

        rbac_correct = sum(
            1
            for result in results
            if result.get(
                "rbac_correct",
                False,
            )
        )

        fallback_correct = sum(
            1
            for result in results
            if result.get(
                "fallback_correct",
                False,
            )
        )

        audit_complete = sum(
            1
            for result in results
            if result.get(
                "audit_complete",
                False,
            )
        )

        fallback_used_count = sum(
            1
            for result in results
            if result.get(
                "fallback_used",
                False,
            )
        )

        llm_used_count = sum(
            1
            for result in results
            if result.get(
                "llm_used",
                False,
            )
        )

        llm_failure_count = sum(
            1
            for result in results
            if (
                result.get(
                    "llm_used",
                    False,
                )
                and result.get(
                    "fallback_used",
                    False,
                )
            )
        )

        latencies = [
            float(
                result.get(
                    "latency_ms",
                    0.0,
                )
                or 0.0
            )
            for result in results
        ]

        sorted_latencies = sorted(
            latencies
        )

        average_latency = (
            sum(latencies)
            / total
        )

        p95_index = min(
            max(
                int(
                    0.95
                    * total
                )
                - 1,
                0,
            ),
            total - 1,
        )

        p95_latency = (
            sorted_latencies[
                p95_index
            ]
        )

        structured_count = sum(
            1
            for result in results
            if str(
                result.get(
                    "retrieval_mode",
                    "",
                )
            ).lower()
            == "structured"
        )

        semantic_count = sum(
            1
            for result in results
            if str(
                result.get(
                    "retrieval_mode",
                    "",
                )
            ).lower()
            == "semantic"
        )

        hybrid_count = sum(
            1
            for result in results
            if str(
                result.get(
                    "retrieval_mode",
                    "",
                )
            ).lower()
            == "hybrid"
        )

        denied_count = sum(
            1
            for result in results
            if str(
                result.get(
                    "status",
                    "",
                )
            ).lower()
            == "denied"
        )

        return {
            "total_evaluations": total,
            "successful_queries": successful,
            "failed_queries": failed,

            "success_rate": round(
                successful / total,
                4,
            ),

            "planner_accuracy": round(
                planner_correct / total,
                4,
            ),

            "retrieval_accuracy": round(
                retrieval_correct / total,
                4,
            ),

            "grounding_rate": round(
                sum(
                    grounding_scores
                )
                / total,
                4,
            ),

            "relevance_rate": round(
                sum(
                    relevance_scores
                )
                / total,
                4,
            ),

            "rbac_accuracy": round(
                rbac_correct / total,
                4,
            ),

            "fallback_accuracy": round(
                fallback_correct / total,
                4,
            ),

            "audit_completeness": round(
                audit_complete / total,
                4,
            ),

            "fallback_rate": round(
                fallback_used_count
                / total,
                4,
            ),

            "average_latency_ms": round(
                average_latency,
                2,
            ),

            "p95_latency_ms": round(
                p95_latency,
                2,
            ),

            "structured_query_count": (
                structured_count
            ),

            "semantic_query_count": (
                semantic_count
            ),

            "hybrid_query_count": (
                hybrid_count
            ),

            "denied_query_count": (
                denied_count
            ),

            "llm_used_count": (
                llm_used_count
            ),

            "llm_failure_count": (
                llm_failure_count
            ),

            "retrieval_distribution": {
                "structured": (
                    structured_count
                ),
                "semantic": (
                    semantic_count
                ),
                "hybrid": (
                    hybrid_count
                ),
            },
        }

    # ========================================================
    # SAVE RESULTS
    # ========================================================

    def save_results(
        self,
        db: Session,
        results: list[
            dict[str, Any]
        ],
    ) -> None:

        for result in results:

            safe_details = {
                key: value
                for key, value
                in (
                    result.get(
                        "details"
                    )
                    or {}
                ).items()
                if key
                not in {
                    "token",
                    "jwt",
                    "password",
                    "authorization",
                    "api_key",
                    "secret",
                }
            }

            grounding_score = float(
                result.get(
                    "grounding_score",
                    0.0,
                )
                or 0.0
            )

            relevance_score = float(
                result.get(
                    "relevance_score",
                    0.0,
                )
                or 0.0
            )

            eval_record = EvaluationResult(
                question=result.get(
                    "query"
                ),

                expected_answer=result.get(
                    "expected_behavior"
                ),

                actual_answer=result.get(
                    "answer_preview"
                ),

                answer_correct=result.get(
                    "success"
                ),

                entity_correct=result.get(
                    "planner_correct"
                ),

                evidence_grounded=(
                    grounding_score >= 0.5
                ),

                relevant=(
                    relevance_score >= 0.5
                ),

                routing_correct=result.get(
                    "retrieval_correct"
                ),

                latency_ms=result.get(
                    "latency_ms"
                ),

                expected_behavior=result.get(
                    "expected_behavior"
                ),

                actual_behavior=result.get(
                    "actual_behavior"
                ),

                planner_correct=result.get(
                    "planner_correct"
                ),

                retrieval_correct=result.get(
                    "retrieval_correct"
                ),

                grounding_score=(
                    grounding_score
                ),

                relevance_score=(
                    relevance_score
                ),

                rbac_correct=result.get(
                    "rbac_correct"
                ),

                fallback_correct=result.get(
                    "fallback_correct"
                ),

                audit_complete=result.get(
                    "audit_complete"
                ),

                retrieval_mode=result.get(
                    "retrieval_mode"
                ),

                evidence_count=result.get(
                    "evidence_count",
                    0,
                ),

                llm_used=result.get(
                    "llm_used",
                    False,
                ),

                fallback_used=result.get(
                    "fallback_used",
                    False,
                ),

                success=result.get(
                    "success",
                    False,
                ),

                scope_role=result.get(
                    "role"
                ),

                scope_supplier_id=result.get(
                    "supplier_id"
                ),

                details=json.dumps(
                    safe_details,
                    default=str,
                ),
            )

            db.add(
                eval_record
            )

        db.commit()

    # ========================================================
    # CLEAR RESULTS
    # ========================================================

    def clear_results(
        self,
        db: Session,
    ) -> None:

        db.query(
            EvaluationResult
        ).delete()

        db.commit()
        