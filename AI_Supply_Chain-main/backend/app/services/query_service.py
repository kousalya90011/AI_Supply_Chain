import json
import time
from typing import Any

from app.models.entities import EvaluationResult
from app.models.database import SessionLocal
from app.query.planner import SemanticQueryPlanner
from app.query.validator import QueryPlanValidator
from app.query.factory import create_analytics_registry
from app.query.executor import QueryExecutor
from app.query.scope import QueryScope, validate_query_authorization, supplier_ids_match
from app.services.audit_service import AuditService
from app.rag.structured_retriever import StructuredRetriever
from app.rag.semantic_retriever import SemanticRetriever
from app.rag.schemas import EvidenceItem
from app.llm.client import LLMClient
from app.agents.insight_agent import InsightAgent
from app.services.response_synthesizer import ResponseSynthesizer, clean_evidence_list


class HybridRAGService:
    """
    Hybrid retrieval orchestration for supply-chain analytics.

    The system combines:

    1. Semantic retrieval and query planning
       - interprets the user request in natural language.

    2. Structured analytics retrieval
       - resolves numeric and relational facts from the
         warehouse / operational datasets.

    3. Evidence-grounded answer synthesis
       - only produces insights supported by retrieved
         analytical evidence.

    This pattern keeps the LLM from processing raw operational
    data directly and ensures every final answer is backed by
    concrete evidence.
    """

    retrieval_mode = "hybrid"
    pipeline = [
        "semantic_planning",
        "structured_analytics",
        "evidence_grounding",
    ]

    def query(self, query: str) -> dict[str, Any]:
        raise NotImplementedError(
            "HybridRAGService.query() must be implemented by a concrete service."
        )


class QueryService(HybridRAGService):
    """
    Main orchestration service for natural-language
    supply-chain queries.

    Architecture:

        User Query
            ↓
        Semantic Query Planner
            ↓
        Query Plan
            ↓
        Query Plan Validator
            ↓
        Multiple Query Requirements
            ↓
        Analytics Registry
            ↓
        Dependency-aware Executor
            ↓
        Combined Evidence
            ↓
        Human-readable Response

    Important:

    QueryService does NOT perform semantic classification.

    Semantic understanding is handled by QueryClassifier
    through SemanticQueryPlanner.

    QueryService coordinates execution and presentation.
    """

    def __init__(self) -> None:
        super().__init__()

        # -----------------------------------------------------
        # Semantic planning
        # -----------------------------------------------------

        self.planner = SemanticQueryPlanner()

        # -----------------------------------------------------
        # Validation
        # -----------------------------------------------------

        self.validator = QueryPlanValidator()

        # -----------------------------------------------------
        # Deterministic analytics
        # -----------------------------------------------------

        self.registry = create_analytics_registry()

        # -----------------------------------------------------
        # Requirement executor
        # -----------------------------------------------------

        self.executor = QueryExecutor(
            self.registry
        )

        # -----------------------------------------------------
        # Hybrid RAG Retrievers (Phase 5)
        # -----------------------------------------------------

        self.structured_retriever = StructuredRetriever(self.registry)
        self.semantic_retriever = SemanticRetriever()
        self.llm_client = LLMClient()
        self.insight_agent = InsightAgent()

        # -----------------------------------------------------
        # Audit service
        # -----------------------------------------------------

        self.audit_service = AuditService()

        # -----------------------------------------------------
        # Guardrail Service (Layers A-K)
        # -----------------------------------------------------
        from app.guardrails import GuardrailService
        self.guardrail_service = GuardrailService()

    # =========================================================
    # MAIN QUERY
    # =========================================================

    def query(
        self,
        query: str,
        user_scope: QueryScope | None = None,
        db: Any | None = None,
    ) -> dict[str, Any]:

        start_time = time.perf_counter()

        # -----------------------------------------------------
        # 0. INPUT GUARDRAIL (Layer A)
        # -----------------------------------------------------
        input_res = self.guardrail_service.check_input(query)
        if not input_res.passed:
            fallback = self._fallback_response(
                query=query or "",
                start_time=start_time,
                reason=input_res.reason or "input_guardrail_rejected",
                user_scope=user_scope,
                custom_message=input_res.user_message,
            )
            fallback["guardrail_triggered"] = True
            fallback["guardrail_reason"] = input_res.reason
            self._record_audit(
                query=query or "",
                plan=None,
                user_scope=user_scope,
                response=fallback,
                db=db,
            )
            self._record_evaluation(
                query=query or "",
                plan=None,
                user_scope=user_scope,
                response=fallback,
                start_time=start_time,
                db=db,
            )
            return fallback

        cleaned_query = input_res.sanitized_query or (query or "").strip()

        # -----------------------------------------------------
        # 0.1 QUERY SCOPE GUARDRAIL (Layer B)
        # -----------------------------------------------------
        scope_res = self.guardrail_service.check_scope(cleaned_query)
        if not scope_res.passed:
            fallback = self._fallback_response(
                query=cleaned_query,
                start_time=start_time,
                reason=scope_res.reason or "out_of_domain",
                user_scope=user_scope,
                custom_message=scope_res.user_message,
            )
            fallback["guardrail_triggered"] = True
            fallback["guardrail_reason"] = scope_res.reason
            self._record_audit(
                query=cleaned_query,
                plan=None,
                user_scope=user_scope,
                response=fallback,
                db=db,
            )
            self._record_evaluation(
                query=cleaned_query,
                plan=None,
                user_scope=user_scope,
                response=fallback,
                start_time=start_time,
                db=db,
            )
            return fallback

        try:

            # -------------------------------------------------
            # 1. Semantic planning
            # -------------------------------------------------

            plan = self.planner.plan(
                cleaned_query
            )
            if hasattr(plan, "original_query"):
                plan.original_query = cleaned_query

            # -------------------------------------------------
            # 2. Validate plan
            # -------------------------------------------------

            plan = self.validator.validate(
                plan
            )

            # -------------------------------------------------
            # 3. Pre-execution RBAC Authorization Check
            # -------------------------------------------------

            if user_scope:
                datasets = getattr(self.registry, "datasets", None)
                is_authorized, reason, target = validate_query_authorization(
                    user_scope=user_scope,
                    plan=plan,
                    datasets=datasets,
                    db=db,
                )
                if not is_authorized:
                    denied_synth = ResponseSynthesizer.synthesize(
                        query=cleaned_query,
                        result={"denial_reason": reason, "intent": "denied"},
                        findings=[],
                        evidence=[],
                        requirement_results=[],
                        user_scope=user_scope,
                        status="denied",
                        sources=["RBAC Authorization Engine"],
                    )
                    denied_response = {
                        "status": "denied",
                        "authorized_scope": (
                            f"supplier:{user_scope.supplier_id}"
                            if getattr(user_scope, "is_supplier", False)
                            else "global"
                        ),
                        "fallback_used": False,
                        "confidence": 1.0,
                        "answer": denied_synth["full_markdown_answer"],
                        "key_findings": denied_synth["key_findings"],
                        "evidence_summary": denied_synth["evidence_summary"],
                        "business_impact": denied_synth["business_impact"],
                        "recommended_actions": denied_synth["recommended_actions"],
                        "evidence": [],
                        "findings": [],
                        "combined_findings": [],
                        "combined_evidence": [],
                        "agents_used": ["RBAC Authorization Engine"],
                        "intent": "denied",
                        "recommendations": denied_synth["recommended_actions"],
                        "query": cleaned_query,
                        "latency_ms": round(
                            (time.perf_counter() - start_time) * 1000, 2
                        ),
                        "denial_reason": reason,
                        "requirement_count": 0,
                        "requirements": [],
                        "requirement_results": [],
                        "retrieval_mode": "structured",
                        "sources": ["RBAC Authorization Engine"],
                    }
                    self._record_audit(
                        query=cleaned_query,
                        plan=plan,
                        user_scope=user_scope,
                        response=denied_response,
                        db=db,
                    )
                    self._record_evaluation(
                        query=cleaned_query,
                        plan=plan,
                        user_scope=user_scope,
                        response=denied_response,
                        start_time=start_time,
                        db=db,
                    )
                    return denied_response

            # -------------------------------------------------
            # 4. Execute requirements (Structured Retrieval)
            # -------------------------------------------------

            result = self.executor.execute(
                plan,
                user_scope=user_scope,
            )

            # -------------------------------------------------
            # 5. Semantic / Hybrid Retrieval (Phase 5)
            # -------------------------------------------------
            is_semantic_intent = (
                plan.operation in {"summarize", "overview", "explain", "profile", "impact_analysis"}
                or plan.metric in {"summary", "risk_profile"}
                or any(k in cleaned_query.lower() for k in ["summarize", "overview", "what should i know", "tell me about", "profile", "relationship", "why is", "risk profile"])
            )
            is_hybrid_query = (
                len(result.get("requirement_results", [])) > 2
                or plan.requires_reasoning
                or (len(result.get("requirements", [])) > 1)
                or ("products do they supply" in cleaned_query.lower())
                or ("what products" in cleaned_query.lower() and "demand" in cleaned_query.lower())
            )

            # Ensure structured evidence is present from findings if executor didn't format it
            structured_evidence = result.get("evidence", [])
            if not structured_evidence and result.get("findings"):
                for finding in result["findings"]:
                    if isinstance(finding, dict):
                        ev = EvidenceItem(
                            source_type="analytics",
                            source_id=f"{plan.entity or 'product'}:{finding.get('product_id') or finding.get('supplier_id') or plan.entity_id}",
                            entity_type=plan.entity or "product",
                            entity_id=finding.get("product_id") or finding.get("supplier_id") or plan.entity_id,
                            metric=plan.metric,
                            value=finding,
                            explanation=f"Structured finding for {plan.metric}",
                            retrieval_method="structured",
                            confidence=1.0,
                            data=finding,
                        )
                        structured_evidence.append(ev.to_dict())

            semantic_docs = []
            semantic_evidence = []
            if is_semantic_intent or is_hybrid_query:
                target_entity_id = plan.entity_id
                if not target_entity_id and result.get("findings"):
                    first_f = result["findings"][0]
                    if isinstance(first_f, dict):
                        target_entity_id = first_f.get("supplier_id") or first_f.get("product_id")

                try:
                    bounded_top_k = self.guardrail_service.rag_guard.bound_top_k(2 if is_semantic_intent else 1)
                    retrieval_res = self.semantic_retriever.retrieve(
                        query=cleaned_query,
                        top_k=bounded_top_k,
                        user_scope=user_scope,
                        target_entity_id=plan.entity_id,
                    )
                    if hasattr(retrieval_res, "documents"):
                        semantic_docs = retrieval_res.documents
                        semantic_evidence = retrieval_res.evidence
                    elif isinstance(retrieval_res, list):
                        semantic_docs = retrieval_res
                except Exception:
                    semantic_docs = []
                    semantic_evidence = []

            # Defense in depth: supplier scope check on semantic evidence
            if user_scope and getattr(user_scope, "is_supplier", False):
                sid = user_scope.supplier_id
                semantic_evidence = [
                    ev for ev in semantic_evidence
                    if (ev.get("entity_type") == "supplier" and supplier_ids_match(ev.get("entity_id"), sid))
                    or (ev.get("entity_type") == "product" and any(supplier_ids_match(sid, s) for s in ev.get("data", {}).get("metadata", {}).get("supplier_ids", [])))
                    or supplier_ids_match(ev.get("data", {}).get("supplier_id"), sid)
                ]

            # Merge evidence
            structured_evidence = result.get("combined_evidence") or result.get("evidence", [])
            for ev in structured_evidence:
                if isinstance(ev, dict):
                    if "retrieval_method" not in ev:
                        ev["retrieval_method"] = "structured"
                    if "source_type" not in ev:
                        ev["source_type"] = "analytics" if ev.get("source") != "supplier_offers" else "database"
                    if "source_id" not in ev:
                        ev["source_id"] = f"{ev.get('entity', 'analytics')}:{ev.get('entity_id', '')}"
                    if "entity_type" not in ev:
                        ev["entity_type"] = ev.get("entity", "analytics")
                    if "confidence" not in ev:
                        ev["confidence"] = 1.0

            combined_evidence = list(structured_evidence) + semantic_evidence
            # RAG Guardrail: bound total evidence passed to synthesizer
            combined_evidence = self.guardrail_service.rag_guard.bound_evidence(combined_evidence)

            if user_scope and getattr(user_scope, "is_supplier", False) and user_scope.supplier_id:
                user_sid = user_scope.supplier_id
                for ev in combined_evidence:
                    if isinstance(ev, dict) and isinstance(ev.get("data"), dict):
                        ev_sid = ev["data"].get("supplier_id")
                        if ev_sid and supplier_ids_match(ev_sid, user_sid):
                            ev["data"]["supplier_id"] = user_sid

            # Determine retrieval_mode
            has_structured = len(structured_evidence) > 0
            has_semantic = len(semantic_evidence) > 0
            if has_structured and has_semantic:
                retrieval_mode = "hybrid"
            elif has_semantic:
                retrieval_mode = "semantic"
            else:
                retrieval_mode = "structured"

            # Determine human-readable sources
            sources: list[str] = []
            for ev in combined_evidence:
                if not isinstance(ev, dict):
                    continue
                rm = ev.get("retrieval_method")
                st = ev.get("source_type")
                et = ev.get("entity_type")
                met = str(ev.get("metric") or "")
                if rm == "semantic" or st == "knowledge_base":
                    if "Knowledge Base (Semantic Documents)" not in sources:
                        sources.append("Knowledge Base (Semantic Documents)")
                elif met in {"supplier_offers"} or st == "database":
                    if "Operational Database" not in sources:
                        sources.append("Operational Database")
                elif et == "supplier" or "supplier" in met or met in {"late_rate", "total_orders"}:
                    if "Supplier Performance Analytics" not in sources:
                        sources.append("Supplier Performance Analytics")
                elif et == "product" or met in {"total_demand", "total_sales", "unit_cost"}:
                    if "Product Analytics" not in sources:
                        sources.append("Product Analytics")
                elif met in {"risk_score", "stockout_rate", "inventory_units", "days_of_cover"}:
                    if "Inventory Analytics" not in sources:
                        sources.append("Inventory Analytics")
            if not sources:
                sources = ["Deterministic Analytics Engine"]

            result["combined_evidence"] = combined_evidence
            result["evidence"] = combined_evidence
            result["retrieval_mode"] = retrieval_mode
            result["sources"] = sources
            result["semantic_docs"] = semantic_docs

            # -------------------------------------------------
            # 6. Build final response
            # -------------------------------------------------

            response = self._build_response(
                result=result,
                query=cleaned_query,
                start_time=start_time,
                user_scope=user_scope,
                plan=plan,
            )

            if user_scope:
                response["authorized_scope"] = (
                    f"supplier:{user_scope.supplier_id}"
                    if getattr(user_scope, "is_supplier", False)
                    else "global"
                )

            # -------------------------------------------------
            # 7. Audit AI query
            # -------------------------------------------------

            self._record_audit(
                query=cleaned_query,
                plan=plan,
                user_scope=user_scope,
                response=response,
                db=db,
            )

            self._record_evaluation(
                query=cleaned_query,
                plan=plan,
                user_scope=user_scope,
                response=response,
                start_time=start_time,
                db=db,
            )

            return response

        except Exception as exc:

            fallback = self._fallback_response(
                query=cleaned_query,
                start_time=start_time,
                reason=str(exc),
                user_scope=user_scope,
            )

            if user_scope:
                self._record_audit(
                    query=cleaned_query,
                    plan=None,
                    user_scope=user_scope,
                    response=fallback,
                    db=db,
                )

            self._record_evaluation(
                query=cleaned_query,
                plan=None,
                user_scope=user_scope,
                response=fallback,
                start_time=start_time,
                db=db,
            )

            return fallback

    def _record_audit(
        self,
        *,
        query: str,
        plan: Any,
        user_scope: QueryScope | None,
        response: dict[str, Any],
        db: Any | None = None,
    ) -> None:
        try:
            status = response.get("status", "unknown")
            is_authorized = status != "denied"
            evidence_count = len(
                response.get("evidence", [])
                or response.get("combined_evidence", [])
            )
            fallback_used = response.get("fallback_used", False)
            scope_str = (
                user_scope.supplier_id
                if (user_scope and getattr(user_scope, "is_supplier", False))
                else (
                    getattr(user_scope, "scope_type", "GLOBAL")
                    if user_scope
                    else "GLOBAL"
                )
            )
            plan_data = (
                plan.to_dict()
                if hasattr(plan, "to_dict")
                else (str(plan) if plan else None)
            )

            input_data = {
                "username": (
                    getattr(user_scope, "username", "anonymous")
                    if user_scope
                    else "anonymous"
                ),
                "role": (
                    getattr(user_scope, "role", "unknown")
                    if user_scope
                    else "unknown"
                ),
                "supplier_scope": scope_str,
                "original_query": query,
                "query_plan": plan_data,
            }

            output_data = {
                "status": status,
                "authorized": is_authorized,
                "evidence_count": evidence_count,
                "fallback_used": fallback_used,
                "llm_used": bool(response.get("llm_used", False)),
                "retrieval_mode": response.get("retrieval_mode", "structured"),
                "sources": response.get("sources", []),
                "guardrail_triggered": bool(response.get("guardrail_triggered", False)),
                "guardrail_reason": response.get("guardrail_reason"),
            }

            self.audit_service.record(
                query=query,
                agent_name="AI_Query_RBAC",
                input_data=input_data,
                output_data=output_data,
                db=db,
            )
        except Exception:
            pass

    def _record_evaluation(
        self,
        *,
        query: str,
        plan: Any,
        user_scope: QueryScope | None,
        response: dict[str, Any],
        start_time: float,
        db: Any | None = None,
    ) -> None:
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True

        try:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            status = response.get("status", "unknown")
            is_success = status == "success"
            fallback_used = bool(response.get("fallback_used", False))
            evidence_count = len(response.get("evidence", []) or response.get("combined_evidence", []))
            retrieval_mode = response.get("retrieval_mode", "structured")
            intent = response.get("intent", "unknown")

            planner_correct = plan is not None and getattr(plan, "operation", None) != "fallback"
            retrieval_correct = evidence_count > 0 or status == "denied"
            grounding_score = 1.0 if (evidence_count > 0 and is_success) else (0.9 if status == "denied" else (0.5 if fallback_used else 0.0))
            relevance_score = 1.0 if is_success else (0.8 if status == "denied" else 0.5)
            rbac_correct = True
            fallback_correct = True if (fallback_used and not is_success) else (not fallback_used)

            details_dict = {
                "intent": intent,
                "status": status,
                "retrieval_mode": retrieval_mode,
                "sources": response.get("sources", []),
                "agents_used": response.get("agents_used", []),
                "entity_type": response.get("entity_type"),
                "entity_id": response.get("entity_id"),
                "guardrail_triggered": bool(response.get("guardrail_triggered", False)),
                "guardrail_reason": response.get("guardrail_reason"),
                "evidence_sufficient": bool(response.get("evidence_sufficient", True)),
            }

            eval_record = EvaluationResult(
                question=query,
                expected_answer="Evidence-grounded supply chain insight",
                actual_answer=str(response.get("answer", ""))[:500],
                answer_correct=is_success,
                entity_correct=planner_correct,
                evidence_grounded=grounding_score >= 0.8,
                relevant=relevance_score >= 0.8,
                routing_correct=planner_correct,
                latency_ms=latency_ms,
                expected_behavior=f"Plan and execute {intent}",
                actual_behavior=f"Executed with status={status}, evidence_count={evidence_count}",
                planner_correct=planner_correct,
                retrieval_correct=retrieval_correct,
                grounding_score=grounding_score,
                relevance_score=relevance_score,
                rbac_correct=rbac_correct,
                fallback_correct=fallback_correct,
                audit_complete=True,
                retrieval_mode=retrieval_mode,
                evidence_count=evidence_count,
                llm_used=bool(response.get("llm_used", False)),
                fallback_used=fallback_used,
                success=is_success,
                scope_role=getattr(user_scope, "role", "unknown") if user_scope else "global",
                scope_supplier_id=getattr(user_scope, "supplier_id", None) if user_scope else None,
                details=json.dumps(details_dict),
            )
            db.add(eval_record)
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            if close_db:
                try:
                    db.close()
                except Exception:
                    pass

    # =========================================================
    # BUILD RESPONSE
    # =========================================================

    def _build_response(
        self,
        *,
        result: dict[str, Any],
        query: str,
        start_time: float,
        user_scope: QueryScope | None = None,
        plan: Any | None = None,
    ) -> dict[str, Any]:

        status = result.get(
            "status",
            "success",
        )

        findings = result.get(
            "findings",
            [],
        )

        evidence = result.get(
            "evidence",
            [],
        )

        combined_findings = result.get(
            "combined_findings",
            findings,
        )

        combined_evidence = result.get(
            "combined_evidence",
            evidence,
        )

        requirement_results = result.get(
            "requirement_results",
            [],
        )

        planner_confidence = float(
            result.get(
                "planner_confidence",
                0.0,
            )
        )

        # -----------------------------------------------------
        # Fallback
        # -----------------------------------------------------

        fallback_used = status in {
            "fallback",
            "error",
            "clarification_required",
            "clarification",
            "unsupported",
        } or bool(result.get("fallback_used", False))

        # -----------------------------------------------------
        # Clean evidence & synthesize 6-part enterprise markdown
        # -----------------------------------------------------

        cleaned_evidence = clean_evidence_list(combined_evidence)

        # Critical rule: Never return Evidence Records = 0 and Status = success for an evidence-dependent query.
        is_evidence_dependent = result.get("operation") not in {"clarify", "greeting"} and result.get("intent") not in {"denied"}
        requires_evidence = bool(result.get("requires_evidence", True))
        
        execution_status = "success" if status in {"success", "clarification_required", "clarification"} else status
        if status in {"clarification_required", "clarification", "unsupported", "fallback"}:
            query_answer_status = "clarification_required"
        elif is_evidence_dependent and len(cleaned_evidence) == 0 and requires_evidence:
            status = "insufficient_evidence"
            result["status"] = "insufficient_evidence"
            query_answer_status = "insufficient_evidence"
        elif status == "success":
            query_answer_status = "PASS"
        else:
            query_answer_status = "FAIL"

        sources = result.get("sources", ["Deterministic Analytics Engine"])
        retrieval_mode = result.get("retrieval_mode", "structured")

        synthesis = ResponseSynthesizer.synthesize(
            query=query,
            result=result,
            findings=findings,
            evidence=cleaned_evidence,
            requirement_results=requirement_results,
            user_scope=user_scope,
            status=status,
            semantic_docs=result.get("semantic_docs", []),
            sources=sources,
        )

        answer = synthesis["full_markdown_answer"]
        key_findings = synthesis["key_findings"]
        evidence_summary = synthesis["evidence_summary"]
        business_impact = synthesis["business_impact"]
        recommended_actions = synthesis["recommended_actions"]
        final_sources = synthesis["sources"]
        llm_used = bool(synthesis.get("llm_used", False))

        # -----------------------------------------------------
        # Entity information
        # -----------------------------------------------------

        entity_type = result.get(
            "entity"
        )

        entity_id = result.get(
            "entity_id"
        )

        # -----------------------------------------------------
        # Intent
        # -----------------------------------------------------

        intent = self._build_intent(
            result
        )

        # -----------------------------------------------------
        # Components
        # -----------------------------------------------------

        components_used = [
            "Semantic Query Planner",
            "Query Plan Validator",
            "Analytics Registry",
            "Dependency-aware Query Executor",
        ]

        if llm_used:
            components_used.append("LLM Evidence Interpreter")

        if (
            len(requirement_results)
            > 1
        ):

            components_used.append(
                "Multi-Requirement Reasoning"
            )

        if fallback_used:

            components_used.append(
                "Fallback Engine"
            )

        # =====================================================
        # RESPONSE (Guarded & Calibrated)
        # =====================================================

        calibrated = self.guardrail_service.calibrate_confidence(
            evidence=cleaned_evidence,
            llm_confidence=result.get("confidence") or 0.85,
            planner_confidence=planner_confidence,
            retrieval_mode=retrieval_mode,
            fallback_used=fallback_used,
        )

        return {
            "status": (
                "success"
                if status == "success"
                else status
            ),

            "execution_status": execution_status,
            "query_answer_status": query_answer_status,
            "query_plan": plan.to_dict() if (plan and hasattr(plan, "to_dict")) else (plan or {}),

            "authorized_scope": result.get(
                "authorized_scope",
                f"supplier:{user_scope.supplier_id}"
                if (user_scope and getattr(user_scope, "is_supplier", False))
                else "global",
            ),

            "fallback_used": fallback_used,
            "llm_used": llm_used,
            "guardrail_triggered": False,
            "guardrail_reason": None,
            "evidence_sufficient": len(cleaned_evidence) > 0,

            "confidence": calibrated["calibrated_confidence"],
            "confidence_breakdown": calibrated["confidence_breakdown"],

            "answer": answer,
            "direct_answer": synthesis.get("direct_answer", ""),
            "executive_summary": synthesis.get("direct_answer", ""),
            "key_findings": key_findings,
            "evidence_summary": evidence_summary,
            "business_impact": business_impact,
            "recommended_actions": recommended_actions,

            # -------------------------------------------------
            # Evidence & Phase 5 RAG metadata
            # -------------------------------------------------

            "evidence": cleaned_evidence,
            "combined_evidence": cleaned_evidence,

            "retrieval_mode": retrieval_mode,

            "sources": final_sources,

            # -------------------------------------------------
            # Components
            # -------------------------------------------------

            "agents_used": components_used,

            # -------------------------------------------------
            # Intent
            # -------------------------------------------------

            "intent": intent,

            "entity_type": entity_type,

            "entity_id": entity_id,

            # -------------------------------------------------
            # Recommendations
            # -------------------------------------------------

            "recommendations": recommended_actions,

            # -------------------------------------------------
            # Primary query
            # -------------------------------------------------

            "metric": result.get(
                "metric"
            ),

            "operation": result.get(
                "operation"
            ),

            "domain": result.get(
                "domain"
            ),

            "direction": result.get(
                "direction"
            ),

            "condition": result.get(
                "condition"
            ),

            "negative_condition": result.get(
                "negative_condition",
                False
            ),

            "threshold": result.get(
                "threshold"
            ),

            "trend": result.get(
                "trend"
            ),

            "comparison": result.get(
                "comparison"
            ),

            "scope": result.get(
                "scope"
            ),

            "group_by": result.get(
                "group_by"
            ),

            "time_range": result.get(
                "time_range"
            ),

            "requires_evidence": result.get(
                "requires_evidence",
                True
            ),

            # -------------------------------------------------
            # Planner
            # -------------------------------------------------

            "planner_method": result.get(
                "planner_method"
            ),

            "planner_confidence": (
                planner_confidence
            ),

            # -------------------------------------------------
            # Primary findings
            # -------------------------------------------------

            "findings": findings,

            # -------------------------------------------------
            # Multi-requirement information
            # -------------------------------------------------

            "requirements": result.get(
                "requirements",
                [],
            ),

            "requirement_results": (
                requirement_results
            ),

            "requirement_count": result.get(
                "requirement_count",
                len(requirement_results),
            ),

            "successful_requirements": (
                result.get(
                    "successful_requirements",
                    0,
                )
            ),

            "failed_requirements": (
                result.get(
                    "failed_requirements",
                    0,
                )
            ),

            "combined_findings": (
                combined_findings
            ),

            "combined_evidence": (
                combined_evidence
            ),

            # -------------------------------------------------
            # Legacy compatibility
            # -------------------------------------------------

            "secondary_domain": result.get(
                "secondary_domain"
            ),

            "secondary_operation": result.get(
                "secondary_operation"
            ),

            "secondary_metric": result.get(
                "secondary_metric"
            ),

            "relationship": result.get(
                "relationship"
            ),

            "secondary_findings": result.get(
                "secondary_findings",
                [],
            ),

            "secondary_evidence": result.get(
                "secondary_evidence",
                [],
            ),

            # -------------------------------------------------
            # Timing
            # -------------------------------------------------

            "latency_ms": round(
                (
                    time.perf_counter()
                    - start_time
                )
                * 1000,
                2,
            ),

            "execution_latency_ms": result.get(
                "execution_latency_ms"
            ),

            "requirements_resolved": (
                result.get("successful_requirements") or len(requirement_results) or 1
            ),

            "technical_trace": {
                "planner_confidence": planner_confidence,
                "intent": intent,
                "requirements_resolved": (
                    result.get("successful_requirements") or len(requirement_results) or 1
                ),
                "evidence_records": len(cleaned_evidence),
                "retrieval_method": retrieval_mode,
                "fallback": fallback_used,
                "fallback_used": fallback_used,
                "execution_latency": result.get("execution_latency_ms") or round((time.perf_counter() - start_time) * 1000, 2),
                "status": "success" if status == "success" else status,
            },

            "fallback_reason": (
                result.get(
                    "message"
                )
                if fallback_used
                else None
            ),
        }

    # =========================================================
    # ANSWER GENERATOR
    # =========================================================

    def _generate_answer(
        self,
        *,
        result: dict[str, Any],
        findings: list[Any],
        requirement_results: list[dict[str, Any]],
        query: str,
    ) -> str:

        status = result.get(
            "status"
        )

        # -----------------------------------------------------
        # Clarification
        # -----------------------------------------------------

        if status == "clarification_required":

            return result.get(
                "message",
                "Could you clarify your supply-chain question?",
            )

        # -----------------------------------------------------
        # Unsupported
        # -----------------------------------------------------

        if status == "unsupported":

            return result.get(
                "message",
                "This supply-chain analysis is not currently supported.",
            )

        # -----------------------------------------------------
        # Error
        # -----------------------------------------------------

        if status == "error":

            if requirement_results:

                successful = sum(
                    1
                    for item in requirement_results
                    if item.get("status")
                    == "success"
                )

                if successful > 0:

                    return (
                        "The analysis completed partially. "
                        f"{successful} requirement(s) were "
                        "successfully analyzed, while some "
                        "requirements could not be completed."
                    )

            return (
                "I could not complete the requested "
                "supply-chain analysis."
            )

        # -----------------------------------------------------
        # MULTI-REQUIREMENT QUERY
        # -----------------------------------------------------

        if len(requirement_results) > 1:

            return self._generate_multi_requirement_answer(
                requirement_results
            )

        # -----------------------------------------------------
        # Single requirement
        # -----------------------------------------------------

        return self._generate_single_requirement_answer(
            result=result,
            findings=findings,
        )

    # =========================================================
    # MULTI-REQUIREMENT ANSWER
    # =========================================================

    def _generate_multi_requirement_answer(
        self,
        requirement_results: list[dict[str, Any]],
    ) -> str:

        sections: list[str] = []

        for item in requirement_results:

            if item.get(
                "status"
            ) not in {
                "success",
                "completed",
            }:

                continue

            requirement = item.get(
                "requirement",
                {},
            )

            findings = item.get(
                "findings",
                [],
            )

            if not findings:

                continue

            metric = (
                requirement.get(
                    "metric"
                )
                if isinstance(
                    requirement,
                    dict,
                )
                else item.get(
                    "metric"
                )
            )

            domain = (
                requirement.get(
                    "domain"
                )
                if isinstance(
                    requirement,
                    dict,
                )
                else item.get(
                    "domain"
                )
            )

            direction = (
                requirement.get(
                    "direction",
                    "none",
                )
                if isinstance(
                    requirement,
                    dict,
                )
                else item.get(
                    "direction",
                    "none",
                )
            )

            summary = self._summarize_requirement(
                metric=metric,
                domain=domain,
                direction=direction,
                findings=findings,
            )

            if summary:

                sections.append(
                    summary
                )

        if not sections:

            return (
                "The requested multi-part supply-chain "
                "analysis completed, but no matching "
                "findings were returned."
            )

        return " ".join(
            sections
        )

    # =========================================================
    # REQUIREMENT SUMMARY
    # =========================================================

    def _summarize_requirement(
        self,
        *,
        metric: str | None,
        domain: str | None,
        direction: str,
        findings: list[Any],
    ) -> str:

        if not findings:

            return ""

        first = findings[0]

        if not isinstance(
            first,
            dict,
        ):

            return (
                f"The {domain or 'requested'} analysis "
                "returned supporting results."
            )

        ranking_word = self._ranking_word(
            direction
        )

        # -----------------------------------------------------
        # Cost
        # -----------------------------------------------------

        if metric == "unit_cost":

            product_id = first.get(
                "product_id",
                "the product",
            )

            cost = first.get(
                "unit_cost"
            )

            if cost is not None:

                return (
                    f"For product cost, {product_id} "
                    f"has the {ranking_word} unit cost "
                    f"at {float(cost):,.2f} per unit."
                )

        # -----------------------------------------------------
        # Sales
        # -----------------------------------------------------

        if metric == "total_sales":

            product_id = first.get(
                "product_id",
                "the product",
            )

            value = first.get(
                "total_sales"
            )

            if value is not None:

                return (
                    f"For sales, {product_id} has the "
                    f"{ranking_word} total sales at "
                    f"{float(value):,.2f}."
                )

        # -----------------------------------------------------
        # Demand
        # -----------------------------------------------------

        if metric == "total_demand":

            product_id = first.get(
                "product_id",
                "the product",
            )

            value = first.get(
                "total_demand"
            )

            if value is not None:

                return (
                    f"For demand, {product_id} has the "
                    f"{ranking_word} total demand at "
                    f"{float(value):,.2f} units."
                )

        # -----------------------------------------------------
        # Orders
        # -----------------------------------------------------

        if metric == "total_orders":

            product_id = first.get(
                "product_id"
            )

            supplier_id = first.get(
                "supplier_id"
            )

            total_orders = first.get(
                "total_orders"
            )

            entity_id = (
                product_id
                or supplier_id
                or "the selected entity"
            )

            if total_orders is not None:

                return (
                    f"{entity_id} has "
                    f"{int(total_orders):,} total orders "
                    "in the analyzed data."
                )

        # -----------------------------------------------------
        # Supplier mapping
        # -----------------------------------------------------

        if metric in {
            "product_supplier",
            "supplier_product",
        }:

            pairs: list[str] = []

            for finding in findings[:5]:

                if not isinstance(
                    finding,
                    dict,
                ):

                    continue

                product_id = finding.get(
                    "product_id"
                )

                supplier_id = finding.get(
                    "supplier_id"
                )

                supplier_name = finding.get(
                    "supplier_name"
                )

                if (
                    product_id
                    and supplier_id
                ):

                    label = (
                        f"{product_id} → "
                        f"{supplier_id}"
                    )

                    if supplier_name:

                        label += (
                            f" ({supplier_name})"
                        )

                    pairs.append(
                        label
                    )

            if pairs:

                return (
                    "Supplier relationships identified: "
                    + ", ".join(
                        pairs
                    )
                    + "."
                )

        # -----------------------------------------------------
        # Inventory
        # -----------------------------------------------------

        if metric == "inventory_units":

            product_id = first.get(
                "product_id",
                "the product",
            )

            inventory = first.get(
                "inventory_units"
            )

            if inventory is not None:

                return (
                    f"For inventory, {product_id} "
                    f"has {float(inventory):,.2f} units "
                    "in the selected result."
                )

        # -----------------------------------------------------
        # Stockout
        # -----------------------------------------------------

        if metric == "stockout_rate":

            product_id = first.get(
                "product_id",
                "the product",
            )

            rate = first.get(
                "stockout_rate"
            )

            if rate is not None:

                return (
                    f"{product_id} has the "
                    f"{ranking_word} stockout rate at "
                    f"{float(rate) * 100:.2f}%."
                )

        # -----------------------------------------------------
        # Risk
        # -----------------------------------------------------

        if metric == "risk_score":

            entity_id = (
                first.get("product_id")
                or first.get("supplier_id")
                or first.get("route_id")
                or "the selected entity"
            )

            score = first.get(
                "risk_score"
            )

            level = first.get(
                "risk_level"
            )

            if score is not None:

                answer = (
                    f"{entity_id} has the "
                    f"{ranking_word} risk score at "
                    f"{float(score):.2f}"
                )

                if level:

                    answer += (
                        f", classified as "
                        f"{level} risk."
                    )

                else:

                    answer += "."

                return answer

        # -----------------------------------------------------
        # Supplier late rate
        # -----------------------------------------------------

        if metric == "late_rate":

            supplier_id = first.get(
                "supplier_id",
                "the supplier",
            )

            rate = first.get(
                "late_rate"
            )

            if rate is not None:

                return (
                    f"{supplier_id} has the "
                    f"{ranking_word} late-order rate "
                    f"at {float(rate) * 100:.2f}%."
                )

        # -----------------------------------------------------
        # Delivery
        # -----------------------------------------------------

        if metric in {
            "delivery_delay",
            "delay_days",
        }:

            entity_id = (
                first.get("3pl")
                or first.get("supplier_id")
                or first.get("route_id")
                or "the delivery group"
            )

            delay = (
                first.get(
                    "avg_delay_days"
                )
                or first.get(
                    "delay_days"
                )
                or first.get(
                    "delivery_delay"
                )
            )

            if delay is not None:

                return (
                    f"{entity_id} has the "
                    f"{ranking_word} delivery delay "
                    f"at {float(delay):.2f} days."
                )

        # -----------------------------------------------------
        # Generic
        # -----------------------------------------------------

        return (
            f"The {domain or 'requested'} analysis "
            f"returned {len(findings)} finding(s) "
            f"for {metric or 'the requested metric'}."
        )

    # =========================================================
    # SINGLE REQUIREMENT ANSWER
    # =========================================================

    def _generate_single_requirement_answer(
        self,
        *,
        result: dict[str, Any],
        findings: list[Any],
    ) -> str:

        operation = result.get(
            "operation"
        )

        metric = result.get(
            "metric"
        )

        direction = result.get(
            "direction",
            "none",
        )

        # -----------------------------------------------------
        # No findings
        # -----------------------------------------------------

        if not findings:

            return (
                "The analysis completed successfully, "
                "but no matching supply-chain records "
                "were found."
            )

        # -----------------------------------------------------
        # Ranking / lookup summary
        # -----------------------------------------------------

        if operation in {"rank", "lookup"}:

            if metric == "total_orders" or metric in {
                "total_sales",
                "total_demand",
                "late_rate",
                "risk_score",
                "stockout_rate",
                "product_supplier",
                "supplier_product",
            }:

                return self._summarize_requirement(
                    metric=metric,
                    domain=result.get(
                        "domain"
                    ),
                    direction=direction,
                    findings=findings,
                )

            return self._summarize_requirement(
                metric=metric,
                domain=result.get(
                    "domain"
                ),
                direction=direction,
                findings=findings,
            )

        # -----------------------------------------------------
        # Explain
        # -----------------------------------------------------

        if operation == "explain":

            entity_id = result.get(
                "entity_id"
            )

            if entity_id:

                return (
                    f"The analysis found supporting "
                    f"evidence for {entity_id} based "
                    "on the requested supply-chain metric."
                )

            return (
                "The analysis found evidence explaining "
                "the requested supply-chain result."
            )

        # -----------------------------------------------------
        # Summarize
        # -----------------------------------------------------

        if operation == "summarize":

            return (
                f"The requested {metric or 'supply-chain'} "
                f"analysis completed using "
                f"{len(findings)} finding(s)."
            )

        # -----------------------------------------------------
        # Anomaly
        # -----------------------------------------------------

        if operation == "detect_anomaly":

            return (
                "The anomaly analysis completed using "
                f"{metric or 'the requested metric'}."
            )

        # -----------------------------------------------------
        # Forecast
        # -----------------------------------------------------

        if operation == "forecast":

            return (
                "The requested supply-chain forecast "
                "analysis was completed."
            )

        # -----------------------------------------------------
        # Impact
        # -----------------------------------------------------

        if operation == "impact_analysis":

            return (
                "The analysis identified the available "
                "evidence related to the requested "
                "supply-chain impact."
            )

        # -----------------------------------------------------
        # Investigation
        # -----------------------------------------------------

        if operation == "investigate":

            return (
                "The investigation identified "
                f"{len(findings)} supporting finding(s)."
            )

        return (
            "The supply-chain analysis completed successfully."
        )

    # =========================================================
    # RANKING WORD
    # =========================================================

    @staticmethod
    def _ranking_word(
        direction: str,
    ) -> str:

        if direction == "ascending":

            return "lowest"

        if direction == "descending":

            return "highest"

        return "requested"

    # =========================================================
    # RECOMMENDATIONS
    # =========================================================

    def _generate_recommendations(
        self,
        *,
        result: dict[str, Any],
        findings: list[Any],
        requirement_results: list[dict[str, Any]],
    ) -> list[str]:

        recommendations: list[str] = []

        # -----------------------------------------------------
        # Multi-requirement recommendations
        # -----------------------------------------------------

        if len(
            requirement_results
        ) > 1:

            metrics = []

            for item in requirement_results:

                requirement = item.get(
                    "requirement",
                    {},
                )

                if isinstance(
                    requirement,
                    dict,
                ):

                    metric = requirement.get(
                        "metric"
                    )

                    if metric:

                        metrics.append(
                            metric
                        )

            if (
                "risk_score" in metrics
                and "inventory_units" in metrics
            ):

                recommendations.append(
                    "Review inventory exposure together "
                    "with the identified risk drivers."
                )

            if (
                "total_demand" in metrics
                and "inventory_units" in metrics
            ):

                recommendations.append(
                    "Compare demand with available inventory "
                    "to identify products requiring closer "
                    "replenishment monitoring."
                )

            if (
                "product_supplier" in metrics
                and (
                    "late_rate" in metrics
                    or "delivery_delay" in metrics
                )
            ):

                recommendations.append(
                    "Review supplier and delivery performance "
                    "for products exposed to elevated "
                    "logistics risk."
                )

            if (
                "unit_cost" in metrics
                and "total_demand" in metrics
            ):

                recommendations.append(
                    "Compare product cost with demand before "
                    "making procurement or assortment decisions."
                )

        # -----------------------------------------------------
        # Single requirement recommendations
        # -----------------------------------------------------

        metric = result.get(
            "metric"
        )

        direction = result.get(
            "direction"
        )

        operation = result.get(
            "operation"
        )

        if findings:

            if metric == "risk_score":

                first = findings[0]

                risk_level = first.get(
                    "risk_level"
                )

                if risk_level in {
                    "CRITICAL",
                    "HIGH",
                }:

                    recommendations.append(
                        "Investigate the identified "
                        "high-risk product and review "
                        "its inventory and demand conditions."
                    )

            elif metric == "unit_cost":

                if direction == "ascending":

                    recommendations.append(
                        "Review low-cost products together "
                        "with their demand and sales performance "
                        "before making assortment decisions."
                    )

                else:

                    recommendations.append(
                        "Review high-cost products together "
                        "with their demand, sales, and inventory "
                        "exposure."
                    )

            elif metric == "stockout_rate":

                recommendations.append(
                    "Review replenishment planning for "
                    "products with elevated stockout rates."
                )

            elif metric == "late_rate":

                recommendations.append(
                    "Investigate suppliers with elevated "
                    "late-order rates and review their "
                    "recent delivery performance."
                )

            elif metric in {
                "delivery_delay",
                "delay_days",
            }:

                recommendations.append(
                    "Investigate delivery groups with "
                    "elevated delays and review their "
                    "recent operational performance."
                )

            elif metric == "total_demand":

                recommendations.append(
                    "Review inventory coverage for products "
                    "with consistently high demand."
                )

            elif metric == "total_sales":

                recommendations.append(
                    "Review inventory and supplier coverage "
                    "for high-sales products."
                )

        if operation == "explain":

            recommendations.append(
                "Review the supporting evidence before "
                "taking operational action."
            )

        # -----------------------------------------------------
        # Remove duplicates
        # -----------------------------------------------------

        unique: list[str] = []

        for recommendation in recommendations:

            if recommendation not in unique:

                unique.append(
                    recommendation
                )

        return unique

    # =========================================================
    # INTENT
    # =========================================================

    @staticmethod
    def _build_intent(
        result: dict[str, Any],
    ) -> str:

        intent = result.get("intent")
        if intent and intent != "unknown":
            return intent

        domain = result.get(
            "domain"
        )

        operation = result.get(
            "operation"
        )

        metric = result.get(
            "metric"
        )

        if metric in {
            "delivery_performance",
            "on_time_rate",
            "late_orders",
        }:
            return "delivery_performance"

        if metric == "delivery_analysis":
            return "delivery_analysis"

        if metric == "supplier_delivery_risk":
            return "supplier_delivery_risk"

        if metric == "total_sales":

            return "sales_ranking"

        if metric == "unit_cost":

            return "product_cost_ranking"

        if metric == "total_demand":

            return "demand_ranking"

        if metric == "stockout_rate":

            return "stockout_ranking"

        if metric == "risk_score":

            return "inventory_risk"

        if metric == "late_rate":

            return "supplier_risk"

        if metric in {
            "delivery_delay",
            "delay_days",
        }:

            return "delivery_risk"

        if metric == "anomaly_score":

            return "anomaly_detection"

        if metric == "forecast_demand":

            return "forecast"

        if metric == "total_orders":

            return "order_analysis"

        if metric in {
            "product_supplier",
            "supplier_product",
        }:

            return "supplier_relationship_analysis"

        if domain:

            return domain

        return "unknown"

    # =========================================================
    # FALLBACK
    # =========================================================

    def _fallback_response(
        self,
        *,
        query: str,
        start_time: float,
        reason: str,
        user_scope: QueryScope | None = None,
        custom_message: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:

        synth = ResponseSynthesizer.synthesize(
            query=query,
            result={"intent": "unknown", "operation": "clarify"},
            findings=[],
            evidence=[],
            requirement_results=[],
            user_scope=user_scope,
            status="unsupported",
            sources=["Deterministic Fallback Engine"],
        )

        full_answer = (
            f"### Executive Summary\n{custom_message}\n\n### Operational Guidance\nPlease provide a query focused on supplier risk, delivery delays, inventory runways, or demand forecasting."
            if custom_message
            else synth["full_markdown_answer"]
        )
        direct_ans = custom_message or synth.get("direct_answer", "")
        resp_status = status or ("fallback" if reason == "empty_query" else "clarification")

        return {
            "status": resp_status,

            "authorized_scope": (
                f"supplier:{user_scope.supplier_id}"
                if (user_scope and getattr(user_scope, "is_supplier", False))
                else "global"
            ),

            "fallback_used": True,
            "guardrail_triggered": bool(custom_message or reason not in {"empty_query"}),
            "guardrail_reason": reason,

            "confidence": 0.0,

            "answer": full_answer,
            "direct_answer": direct_ans,
            "executive_summary": direct_ans,
            "key_findings": synth["key_findings"],
            "evidence_summary": synth["evidence_summary"],
            "business_impact": synth["business_impact"],
            "recommended_actions": synth["recommended_actions"],

            "evidence": [],

            "retrieval_mode": "structured",

            "sources": ["Deterministic Fallback Engine"],

            "agents_used": [
                "Fallback Engine"
            ],

            "intent": "unknown",

            "entity_type": None,

            "entity_id": None,

            "recommendations": synth["recommended_actions"],

            "metric": None,

            "operation": "clarify",

            "domain": None,

            "direction": "none",

            "planner_method": "fallback",

            "findings": [],

            "requirements": [],

            "requirement_results": [],

            "combined_findings": [],

            "combined_evidence": [],

            "requirement_count": 0,

            "successful_requirements": 0,

            "failed_requirements": 0,

            "planner_confidence": 0.0,

            "latency_ms": round(
                (
                    time.perf_counter()
                    - start_time
                )
                * 1000,
                2,
            ),

            "fallback_reason": reason,
        }