from __future__ import annotations

import time
from typing import Any

from app.query.registry import AnalyticsRegistry
from app.query.schema import QueryPlan, QueryRequirement
from app.query.scope import get_supplier_authorized_products, supplier_ids_match


class QueryExecutor:
    """
    Executes validated QueryPlans using deterministic analytics.

    Architecture:

        User Query
            ↓
        Semantic Query Planner
            ↓
        QueryPlan
            ↓
        QueryRequirements[]
            ↓
        Dependency-aware execution
            ↓
        Analytics Registry
            ↓
        Deterministic Findings
            ↓
        Combined Evidence
            ↓
        QueryService / Insight Generator

    Important:

    The executor does NOT understand natural language.

    It does NOT decide what the user means.

    It only executes the structured requirements produced
    by the semantic planner.

    There is no artificial limit on the number of requirements.
    """

    def __init__(
        self,
        registry: AnalyticsRegistry,
    ) -> None:

        self.registry = registry

    # =========================================================
    # PUBLIC EXECUTION
    # =========================================================

    def execute(
        self,
        plan: QueryPlan,
        user_scope: Any | None = None,
    ) -> dict[str, Any]:

        start_time = time.perf_counter()

        # -----------------------------------------------------
        # Clarification
        # -----------------------------------------------------

        if plan.operation == "clarify":

            return self._base_response(
                plan=plan,
                status="clarification_required",
                start_time=start_time,
            )

        # -----------------------------------------------------
        # Determine requirements
        # -----------------------------------------------------

        requirements = list(
            getattr(
                plan,
                "requirements",
                [],
            )
            or []
        )

        # -----------------------------------------------------
        # Backward compatibility
        #
        # If an old plan does not contain requirements,
        # create one requirement from the primary plan.
        # -----------------------------------------------------

        if not requirements:

            if not plan.metric:

                return self._base_response(
                    plan=plan,
                    status="clarification_required",
                    start_time=start_time,
                )

            requirements = [
                self._requirement_from_plan(plan)
            ]

        # =====================================================
        # EXECUTE REQUIREMENTS
        # =====================================================

        requirement_results: list[dict[str, Any]] = []

        for index, requirement in enumerate(
            requirements
        ):

            try:

                result = self._execute_requirement(
                    plan=plan,
                    requirement=requirement,
                    requirement_index=index,
                    previous_results=requirement_results,
                    user_scope=user_scope,
                )

                requirement_results.append(
                    result
                )

            except Exception as exc:

                requirement_results.append(
                    {
                        "index": index,
                        "status": "error",
                        "requirement": self._requirement_to_dict(
                            requirement
                        ),
                        "findings": [],
                        "evidence": [],
                        "error": str(exc),
                    }
                )

        # =====================================================
        # COMBINE RESULTS
        # =====================================================

        primary_result = (
            requirement_results[0]
            if requirement_results
            else {}
        )

        primary_findings = self._extract_findings(
            primary_result
        )

        primary_evidence = self._extract_evidence(
            primary_result
        )

        combined_findings: list[dict[str, Any]] = []

        combined_evidence: list[dict[str, Any]] = []

        successful_requirements = 0

        failed_requirements = 0

        for result in requirement_results:

            status = result.get(
                "status",
                "success",
            )

            if status in {
                "success",
                "completed",
            }:

                successful_requirements += 1

            elif status in {
                "error",
                "unsupported",
            }:

                failed_requirements += 1

            combined_findings.extend(
                self._extract_findings(
                    result
                )
            )

            combined_evidence.extend(
                self._extract_evidence(
                    result
                )
            )

        # =====================================================
        # OVERALL STATUS
        # =====================================================

        if not requirement_results:

            overall_status = "error"

        elif successful_requirements == 0:

            if failed_requirements > 0:

                overall_status = "error"

            else:

                overall_status = "unsupported"

        else:

            # Partial success is still useful.
            overall_status = "success"

        # =====================================================
        # BACKWARD-COMPATIBLE SECONDARY INFORMATION
        # =====================================================

        secondary_result = (
            requirement_results[1]
            if len(requirement_results) > 1
            else {}
        )

        secondary_requirement = (
            requirements[1]
            if len(requirements) > 1
            else None
        )

        # -----------------------------------------------------
        # Scope enforcement on combined results
        # -----------------------------------------------------
        authorized_scope_str = (
            f"supplier:{user_scope.supplier_id}"
            if (user_scope and getattr(user_scope, "is_supplier", False))
            else "global"
        )

        if user_scope and getattr(user_scope, "is_supplier", False):
            user_sid = user_scope.supplier_id or ""
            auth_products = get_supplier_authorized_products(user_sid)

            filtered_comb_findings = []
            for f in combined_findings:
                if isinstance(f, dict):
                    sid = f.get("supplier_id")
                    if sid and not supplier_ids_match(user_sid, sid):
                        continue
                    pid = f.get("product_id")
                    if pid and str(pid).upper() not in auth_products:
                        continue
                    filtered_comb_findings.append(f)
                else:
                    filtered_comb_findings.append(f)
            combined_findings = filtered_comb_findings

            filtered_comb_evidence = []
            for e in combined_evidence:
                data = e.get("data") if isinstance(e, dict) else None
                if isinstance(data, dict):
                    sid = data.get("supplier_id")
                    if sid and not supplier_ids_match(user_sid, sid):
                        continue
                    pid = data.get("product_id")
                    if pid and str(pid).upper() not in auth_products:
                        continue
                    filtered_comb_evidence.append(e)
                else:
                    filtered_comb_evidence.append(e)
            combined_evidence = filtered_comb_evidence

        # =====================================================
        # FINAL RESPONSE
        # =====================================================

        return {
            "status": overall_status,
            "authorized_scope": authorized_scope_str,

            "query": plan.original_query,

            # -------------------------------------------------
            # Primary plan
            # -------------------------------------------------

            "metric": plan.metric,

            "operation": plan.operation,

            "domain": plan.domain,

            "direction": plan.direction,

            "entity": plan.entity,

            "entity_id": plan.entity_id,

            # -------------------------------------------------
            # Primary findings
            # -------------------------------------------------

            "findings": primary_findings,

            "evidence": primary_evidence,

            # -------------------------------------------------
            # All requirements
            # -------------------------------------------------

            "requirements": [
                self._serialize_requirement_result(
                    result
                )
                for result in requirement_results
            ],

            "requirement_results": requirement_results,

            "requirement_count": len(
                requirement_results
            ),

            "successful_requirements": (
                successful_requirements
            ),

            "failed_requirements": (
                failed_requirements
            ),

            # -------------------------------------------------
            # Combined
            # -------------------------------------------------

            "combined_findings": combined_findings,

            "combined_evidence": combined_evidence,

            # -------------------------------------------------
            # Backward compatibility
            # -------------------------------------------------

            "secondary_domain": (
                secondary_requirement.domain
                if secondary_requirement
                else getattr(
                    plan,
                    "secondary_domain",
                    None,
                )
            ),

            "secondary_operation": (
                secondary_requirement.operation
                if secondary_requirement
                else getattr(
                    plan,
                    "secondary_operation",
                    None,
                )
            ),

            "secondary_metric": (
                secondary_requirement.metric
                if secondary_requirement
                else getattr(
                    plan,
                    "secondary_metric",
                    None,
                )
            ),

            "relationship": (
                secondary_requirement.relationship
                if secondary_requirement
                else getattr(
                    plan,
                    "relationship",
                    None,
                )
            ),

            "secondary_findings": (
                self._extract_findings(
                    secondary_result
                )
            ),

            "secondary_evidence": (
                self._extract_evidence(
                    secondary_result
                )
            ),

            # -------------------------------------------------
            # Planner information
            # -------------------------------------------------

            "planner_confidence": (
                plan.confidence
            ),

            "planner_method": (
                plan.planner_method
            ),

            # -------------------------------------------------
            # Timing
            # -------------------------------------------------

            "execution_latency_ms": (
                self._latency(start_time)
            ),
        }

    # =========================================================
    # REQUIREMENT EXECUTION
    # =========================================================

    def _execute_requirement(
        self,
        *,
        plan: QueryPlan,
        requirement: QueryRequirement,
        requirement_index: int,
        previous_results: list[dict[str, Any]],
        user_scope: Any | None = None,
    ) -> dict[str, Any]:

        # -----------------------------------------------------
        # Resolve dependency
        # -----------------------------------------------------

        dependency_result = self._resolve_dependency(
            requirement=requirement,
            previous_results=previous_results,
        )

        # -----------------------------------------------------
        # Build executable QueryPlan
        # -----------------------------------------------------

        requirement_plan = self._build_requirement_plan(
            parent_plan=plan,
            requirement=requirement,
            dependency_result=dependency_result,
            user_scope=user_scope,
        )

        if user_scope and getattr(user_scope, "is_supplier", False):
            user_sid = user_scope.supplier_id or ""
            auth_products = get_supplier_authorized_products(user_sid)
            requirement_plan.filters["supplier_id"] = user_sid
            requirement_plan.filters["supplier_ids"] = [user_sid]
            requirement_plan.filters["authorized_products"] = list(auth_products)

            if requirement_plan.entity == "supplier":
                if not requirement_plan.entity_id or supplier_ids_match(user_sid, requirement_plan.entity_id):
                    requirement_plan.entity_id = user_sid
                else:
                    return {
                        "index": requirement_index,
                        "status": "denied",
                        "requirement": self._requirement_to_dict(requirement),
                        "findings": [],
                        "evidence": [],
                        "error": "Supplier outside authorized scope",
                    }
            elif requirement_plan.entity == "product" and requirement_plan.entity_id:
                if str(requirement_plan.entity_id).upper() not in auth_products:
                    return {
                        "index": requirement_index,
                        "status": "denied",
                        "requirement": self._requirement_to_dict(requirement),
                        "findings": [],
                        "evidence": [],
                        "error": "Product outside authorized supplier scope",
                    }

        # -----------------------------------------------------
        # Validate metric
        # -----------------------------------------------------

        if not requirement_plan.metric:

            return {
                "index": requirement_index,
                "status": "unsupported",
                "requirement": self._requirement_to_dict(
                    requirement
                ),
                "findings": [],
                "evidence": [],
                "error": (
                    "Query requirement does not specify "
                    "an analytics metric."
                ),
            }

        # -----------------------------------------------------
        # Execute deterministic analytics
        # -----------------------------------------------------

        result = self._execute_registered_metric(
            metric=requirement_plan.metric,
            plan=requirement_plan,
        )

        # -----------------------------------------------------
        # Normalize result
        # -----------------------------------------------------

        status = result.get(
            "status",
            "success",
        )

        findings = self._extract_findings(
            result
        )

        evidence = self._extract_evidence(
            result
        )

        # -----------------------------------------------------
        # Add requirement traceability
        # -----------------------------------------------------

        enriched_evidence = []

        for item in evidence:

            if not isinstance(
                item,
                dict,
            ):

                continue

            evidence_item = dict(item)

            evidence_item.setdefault(
                "requirement_index",
                requirement_index,
            )

            evidence_item.setdefault(
                "requirement_metric",
                requirement.metric,
            )

            evidence_item.setdefault(
                "requirement_domain",
                requirement.domain,
            )

            enriched_evidence.append(evidence_item)

        # -----------------------------------------------------
        # Scope filtering on requirement findings and evidence
        # -----------------------------------------------------
        if user_scope and getattr(user_scope, "is_supplier", False):
            user_sid = user_scope.supplier_id or ""
            auth_products = get_supplier_authorized_products(user_sid)
            filtered_findings = []
            for f in findings:
                if isinstance(f, dict):
                    sid = f.get("supplier_id")
                    if sid and not supplier_ids_match(user_sid, sid):
                        continue
                    pid = f.get("product_id")
                    if pid and str(pid).upper() not in auth_products:
                        continue
                    filtered_findings.append(f)
                else:
                    filtered_findings.append(f)
            findings = filtered_findings

            filtered_evidence = []
            for e in enriched_evidence:
                data = e.get("data") if isinstance(e, dict) else None
                if isinstance(data, dict):
                    sid = data.get("supplier_id")
                    if sid and not supplier_ids_match(user_sid, sid):
                        continue
                    pid = data.get("product_id")
                    if pid and str(pid).upper() not in auth_products:
                        continue
                    filtered_evidence.append(e)
                else:
                    filtered_evidence.append(e)
            enriched_evidence = filtered_evidence

        return {
            "index": requirement_index,

            "status": status,

            "requirement": self._requirement_to_dict(
                requirement
            ),

            "resolved_filters": (
                requirement_plan.filters
            ),

            "dependency": (
                requirement.depends_on
            ),

            "metric": requirement_plan.metric,

            "domain": requirement_plan.domain,

            "operation": requirement_plan.operation,

            "direction": requirement_plan.direction,

            "entity": requirement_plan.entity,

            "entity_id": requirement_plan.entity_id,

            "findings": findings,

            "evidence": enriched_evidence,

            "message": result.get(
                "message"
            ),

            "error": result.get(
                "error"
            ),
        }

    # =========================================================
    # DEPENDENCY RESOLUTION
    # =========================================================

    def _resolve_dependency(
        self,
        *,
        requirement: QueryRequirement,
        previous_results: list[dict[str, Any]],
    ) -> dict[str, Any] | None:

        dependency_index = requirement.depends_on

        if dependency_index is None:

            return None

        if not isinstance(
            dependency_index,
            int,
        ):

            return None

        if dependency_index < 0:

            return None

        if dependency_index >= len(
            previous_results
        ):

            return None

        return previous_results[
            dependency_index
        ]

    # =========================================================
    # BUILD REQUIREMENT PLAN
    # =========================================================

    def _build_requirement_plan(
        self,
        *,
        parent_plan: QueryPlan,
        requirement: QueryRequirement,
        dependency_result: dict[str, Any] | None,
        user_scope: Any | None = None,
    ) -> QueryPlan:

        filters = dict(
            requirement.filters
            or {}
        )

        # -----------------------------------------------------
        # Resolve dependency findings
        # -----------------------------------------------------

        dependency_findings = []

        if dependency_result:

            dependency_findings = (
                self._extract_findings(
                    dependency_result
                )
            )

        # -----------------------------------------------------
        # Determine relationship source entity
        # -----------------------------------------------------

        dependency_domain = None

        if dependency_result:

            dependency_requirement = (
                dependency_result.get(
                    "requirement",
                    {}
                )
            )

            if isinstance(
                dependency_requirement,
                dict,
            ):

                dependency_domain = (
                    dependency_requirement.get(
                        "domain"
                    )
                )

        # -----------------------------------------------------
        # Extract entity IDs
        # -----------------------------------------------------

        product_ids = self._extract_product_ids(
            dependency_findings
        )

        supplier_ids = self._extract_supplier_ids(
            dependency_findings
        )

        route_ids = self._extract_route_ids(
            dependency_findings
        )

        # -----------------------------------------------------
        # Apply dependency filters
        #
        # This is generic enough for multiple chained
        # requirements without hard-coding a maximum depth.
        # -----------------------------------------------------

        if product_ids:

            if (
                requirement.domain
                in {
                    "supplier",
                    "demand",
                    "inventory",
                    "order",
                    "delivery",
                    "forecast",
                    "product",
                }
            ):

                filters.setdefault(
                    "product_ids",
                    product_ids,
                )

        if supplier_ids:

            if (
                requirement.domain
                in {
                    "product",
                    "order",
                    "delivery",
                    "supplier",
                }
            ):

                filters.setdefault(
                    "supplier_ids",
                    supplier_ids,
                )

        if route_ids:

            if (
                requirement.domain
                in {
                    "route",
                    "delivery",
                    "order",
                }
            ):

                filters.setdefault(
                    "route_ids",
                    route_ids,
                )

        # -----------------------------------------------------
        # Explicit requirement entity ID
        # -----------------------------------------------------

        entity_id = requirement.entity_id

        if entity_id:

            if requirement.entity == "product":

                filters.setdefault(
                    "product_ids",
                    [entity_id],
                )

            elif requirement.entity == "supplier":

                filters.setdefault(
                    "supplier_ids",
                    [entity_id],
                )

            elif requirement.entity == "route":

                filters.setdefault(
                    "route_ids",
                    [entity_id],
                )

        # -----------------------------------------------------
        # Parent filters
        #
        # Only inherit them when the requirement did not
        # explicitly define its own filter.
        # -----------------------------------------------------

        if not filters:

            filters = dict(
                parent_plan.filters
                or {}
            )

        if user_scope and getattr(user_scope, "is_supplier", False):
            user_sid = user_scope.supplier_id or ""
            auth_products = get_supplier_authorized_products(user_sid)
            filters["supplier_id"] = user_sid
            if "supplier_ids" in filters:
                filters["supplier_ids"] = [
                    s for s in filters["supplier_ids"]
                    if supplier_ids_match(user_sid, s)
                ]
                if not filters["supplier_ids"]:
                    filters["supplier_ids"] = [user_sid]
            else:
                filters["supplier_ids"] = [user_sid]

            if "product_ids" in filters:
                filters["product_ids"] = [
                    p for p in filters["product_ids"]
                    if str(p).upper() in auth_products
                ]
            else:
                filters["product_ids"] = list(auth_products)
            filters["authorized_products"] = list(auth_products)

        # -----------------------------------------------------
        # Build QueryPlan
        # -----------------------------------------------------

        return QueryPlan(
            domain=requirement.domain,
            operation=(
                requirement.operation
                or "lookup"
            ),
            metric=requirement.metric,
            direction=(
                requirement.direction
                or "none"
            ),
            entity=requirement.entity,
            entity_id=entity_id,
            filters=filters,
            confidence=(
                requirement.confidence
                or parent_plan.confidence
            ),
            original_query=(
                parent_plan.original_query
            ),
            planner_method=(
                "requirement_execution"
            ),
        )

    # =========================================================
    # REGISTERED ANALYTICS
    # =========================================================

    def _execute_registered_metric(
        self,
        *,
        metric: str,
        plan: QueryPlan,
    ) -> dict[str, Any]:

        analyzer = self.registry.get(
            metric
        )

        if analyzer is None:

            return {
                "status": "unsupported",

                "metric": metric,

                "operation": plan.operation,

                "domain": plan.domain,

                "direction": plan.direction,

                "entity": plan.entity,

                "entity_id": plan.entity_id,

                "findings": [],

                "evidence": [],

                "error": (
                    "No analytics implementation "
                    f"is registered for metric "
                    f"'{metric}'."
                ),
            }

        try:

            # -------------------------------------------------
            # execute()
            # -------------------------------------------------

            if (
                hasattr(
                    analyzer,
                    "execute",
                )
                and callable(
                    analyzer.execute
                )
            ):

                result = analyzer.execute(
                    plan
                )

                return self._normalize_result(
                    result=result,
                    plan=plan,
                )

            # -------------------------------------------------
            # analyze()
            # -------------------------------------------------

            if (
                hasattr(
                    analyzer,
                    "analyze",
                )
                and callable(
                    analyzer.analyze
                )
            ):

                result = analyzer.analyze(
                    plan
                )

                return self._normalize_result(
                    result=result,
                    plan=plan,
                )

            # -------------------------------------------------
            # run()
            # -------------------------------------------------

            if (
                hasattr(
                    analyzer,
                    "run",
                )
                and callable(
                    analyzer.run
                )
            ):

                result = analyzer.run(
                    plan
                )

                return self._normalize_result(
                    result=result,
                    plan=plan,
                )

            # -------------------------------------------------
            # Callable
            # -------------------------------------------------

            if callable(
                analyzer
            ):

                result = analyzer(
                    plan
                )

                return self._normalize_result(
                    result=result,
                    plan=plan,
                )

            raise TypeError(
                f"Registered analytics '{metric}' "
                "is not executable."
            )

        except Exception as exc:

            return {
                "status": "error",

                "metric": metric,

                "operation": plan.operation,

                "domain": plan.domain,

                "direction": plan.direction,

                "entity": plan.entity,

                "entity_id": plan.entity_id,

                "findings": [],

                "evidence": [],

                "error": str(exc),
            }

    # =========================================================
    # REQUIREMENT FROM PRIMARY PLAN
    # =========================================================

    @staticmethod
    def _requirement_from_plan(
        plan: QueryPlan,
    ) -> QueryRequirement:

        return QueryRequirement(
            domain=plan.domain,
            operation=plan.operation,
            metric=plan.metric,
            direction=plan.direction,
            entity=plan.entity,
            entity_id=plan.entity_id,
            relationship=plan.relationship,
            depends_on=None,
            filters=dict(
                plan.filters
                or {}
            ),
            purpose=(
                "Primary query requirement"
            ),
            confidence=plan.confidence,
        )

    # =========================================================
    # PRODUCT IDS
    # =========================================================

    @staticmethod
    def _extract_product_ids(
        findings: list[dict[str, Any]],
    ) -> list[str]:

        product_ids: list[str] = []

        for finding in findings:

            if not isinstance(
                finding,
                dict,
            ):

                continue

            product_id = finding.get(
                "product_id"
            )

            if product_id is None:

                continue

            product_id = str(
                product_id
            )

            if product_id not in product_ids:

                product_ids.append(
                    product_id
                )

        return product_ids

    # =========================================================
    # SUPPLIER IDS
    # =========================================================

    @staticmethod
    def _extract_supplier_ids(
        findings: list[dict[str, Any]],
    ) -> list[str]:

        supplier_ids: list[str] = []

        for finding in findings:

            if not isinstance(
                finding,
                dict,
            ):

                continue

            supplier_id = finding.get(
                "supplier_id"
            )

            if supplier_id is None:

                continue

            supplier_id = str(
                supplier_id
            )

            if supplier_id not in supplier_ids:

                supplier_ids.append(
                    supplier_id
                )

        return supplier_ids

    # =========================================================
    # ROUTE IDS
    # =========================================================

    @staticmethod
    def _extract_route_ids(
        findings: list[dict[str, Any]],
    ) -> list[str]:

        route_ids: list[str] = []

        for finding in findings:

            if not isinstance(
                finding,
                dict,
            ):

                continue

            route_id = finding.get(
                "route_id"
            )

            if route_id is None:

                continue

            route_id = str(
                route_id
            )

            if route_id not in route_ids:

                route_ids.append(
                    route_id
                )

        return route_ids

    # =========================================================
    # REQUIREMENT SERIALIZATION
    # =========================================================

    @staticmethod
    def _requirement_to_dict(
        requirement: QueryRequirement,
    ) -> dict[str, Any]:

        if hasattr(
            requirement,
            "model_dump",
        ):

            return requirement.model_dump()

        if hasattr(
            requirement,
            "dict",
        ):

            return requirement.dict()

        return {
            "domain": requirement.domain,
            "operation": requirement.operation,
            "metric": requirement.metric,
            "direction": requirement.direction,
            "entity": requirement.entity,
            "entity_id": requirement.entity_id,
            "relationship": requirement.relationship,
            "depends_on": requirement.depends_on,
            "filters": requirement.filters,
            "purpose": requirement.purpose,
            "confidence": requirement.confidence,
        }

    @staticmethod
    def _serialize_requirement_result(
        result: dict[str, Any],
    ) -> dict[str, Any]:

        return {
            "index": result.get(
                "index"
            ),

            "status": result.get(
                "status"
            ),

            "requirement": result.get(
                "requirement",
                {},
            ),

            "dependency": result.get(
                "dependency"
            ),

            "resolved_filters": result.get(
                "resolved_filters",
                {},
            ),

            "metric": result.get(
                "metric"
            ),

            "domain": result.get(
                "domain"
            ),

            "operation": result.get(
                "operation"
            ),

            "direction": result.get(
                "direction"
            ),

            "findings": result.get(
                "findings",
                [],
            ),

            "evidence": result.get(
                "evidence",
                [],
            ),

            "message": result.get(
                "message"
            ),

            "error": result.get(
                "error"
            ),
        }

    # =========================================================
    # RESULT NORMALIZATION
    # =========================================================

    @staticmethod
    def _normalize_result(
        *,
        result: Any,
        plan: QueryPlan,
    ) -> dict[str, Any]:

        if isinstance(
            result,
            dict,
        ):

            normalized = dict(
                result
            )

            normalized.setdefault(
                "status",
                "success",
            )

            normalized.setdefault(
                "findings",
                [],
            )

            normalized.setdefault(
                "evidence",
                [],
            )

            return normalized

        if isinstance(
            result,
            list,
        ):

            return {
                "status": "success",
                "findings": result,
                "evidence": [
                    {
                        "source": (
                            plan.metric
                            or "analytics"
                        ),
                        "metric": plan.metric,
                        "entity": plan.entity,
                        "entity_id": plan.entity_id,
                        "data": item,
                    }
                    for item in result
                ],
            }

        return {
            "status": "success",

            "findings": [
                result
            ],

            "evidence": [
                {
                    "source": (
                        plan.metric
                        or "analytics"
                    ),
                    "metric": plan.metric,
                    "entity": plan.entity,
                    "entity_id": plan.entity_id,
                    "data": result,
                }
            ],
        }

    # =========================================================
    # FINDINGS
    # =========================================================

    @staticmethod
    def _extract_findings(
        result: dict[str, Any],
    ) -> list[dict[str, Any]]:

        if not result:

            return []

        findings = result.get(
            "findings",
            [],
        )

        if isinstance(
            findings,
            list,
        ):

            return findings

        if isinstance(
            findings,
            dict,
        ):

            return [
                findings
            ]

        return []

    # =========================================================
    # EVIDENCE
    # =========================================================

    @staticmethod
    def _extract_evidence(
        result: dict[str, Any],
    ) -> list[dict[str, Any]]:

        if not result:

            return []

        evidence = result.get(
            "evidence",
            [],
        )

        if isinstance(
            evidence,
            list,
        ):

            return evidence

        if isinstance(
            evidence,
            dict,
        ):

            return [
                evidence
            ]

        return []

    # =========================================================
    # BASE RESPONSE
    # =========================================================

    def _base_response(
        self,
        *,
        plan: QueryPlan,
        status: str,
        start_time: float,
    ) -> dict[str, Any]:

        return {
            "status": status,

            "query": plan.original_query,

            "metric": plan.metric,

            "operation": plan.operation,

            "domain": plan.domain,

            "direction": plan.direction,

            "entity": plan.entity,

            "entity_id": plan.entity_id,

            "findings": [],

            "evidence": [],

            "requirements": [],

            "requirement_results": [],

            "requirement_count": 0,

            "successful_requirements": 0,

            "failed_requirements": 0,

            "combined_findings": [],

            "combined_evidence": [],

            # Backward compatibility

            "secondary_domain": getattr(
                plan,
                "secondary_domain",
                None,
            ),

            "secondary_operation": getattr(
                plan,
                "secondary_operation",
                None,
            ),

            "secondary_metric": getattr(
                plan,
                "secondary_metric",
                None,
            ),

            "relationship": getattr(
                plan,
                "relationship",
                None,
            ),

            "secondary_findings": [],

            "secondary_evidence": [],

            "planner_confidence": (
                plan.confidence
            ),

            "planner_method": (
                plan.planner_method
            ),

            "execution_latency_ms": (
                self._latency(
                    start_time
                )
            ),
        }

    # =========================================================
    # LATENCY
    # =========================================================

    @staticmethod
    def _latency(
        start_time: float,
    ) -> float:

        return round(
            (
                time.perf_counter()
                - start_time
            )
            * 1000,
            2,
        )
    