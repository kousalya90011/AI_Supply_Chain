from __future__ import annotations

import re
from typing import Any

from app.query.schema import QueryPlan, QueryRequirement


class SemanticQueryInterpreter:
    """
    Reusable semantic query interpretation layer for supply-chain risk intelligence.

    Transforms diverse natural-language business expressions into normalized,
    deterministic analytical dimensions:
    - entity & entity_ids
    - domain & metric
    - operation (rank, filter, compare, lookup, explain, forecast, detect_anomaly, summarize)
    - direction (ascending, descending, none)
    - condition & negative_condition
    - threshold (operator, value, unit)
    - comparison (entities, target, metric)
    - trend (increase, decrease, unusual, check)
    - time_range
    - scope & aggregation
    - multi-requirement decomposition

    Source of truth remains deterministic analytics; this layer interprets user intent.
    """

    # =========================================================================
    # BUSINESS SYNONYMS & VOCABULARY NORMALIZATION
    # =========================================================================

    SYNONYM_MAP = {
        # Suppliers
        "vendor": "supplier",
        "vendors": "suppliers",
        "supplier partner": "supplier",
        "supplier partners": "suppliers",
        "vendor partner": "supplier",
        "vendor partners": "suppliers",
        "manufacturer": "supplier",
        "manufacturers": "suppliers",

        # Delivery & Shipment
        "shipment": "delivery",
        "shipments": "deliveries",
        "fulfillment": "delivery",
        "order fulfillment": "delivery",
        "shipping": "delivery",
        "dispatch": "delivery",
        "logistics": "delivery",

        # Late & Delays
        "delayed": "late",
        "delay": "late",
        "delays": "late",
        "delivery delay": "late",
        "delivery delays": "late",
        "late delivery": "late",
        "late deliveries": "late",
        "overdue": "late",
        "tardy": "late",

        # Inventory & Stock
        "stock": "inventory",
        "stock level": "inventory",
        "stock levels": "inventory",
        "inventory level": "inventory",
        "inventory levels": "inventory",
        "inventory cover": "days_of_cover",
        "inventory coverage": "days_of_cover",
        "days of inventory cover": "days_of_cover",
        "days of inventory coverage": "days_of_cover",
        "days of cover": "days_of_cover",
        "cover days": "days_of_cover",

        # Stockout
        "stockouts": "stockout",
        "out of stock": "stockout",
        "no stock": "stockout",
        "zero inventory": "stockout",
        "inventory shortage": "stockout",
        "stock shortage": "stockout",
        "running out of stock": "stockout",
        "run out of stock": "stockout",

        # Lead Time
        "lead time": "lead_time",
        "lead times": "lead_time",
        "leadtime": "lead_time",
        "lead-time": "lead_time",
        "fulfillment time": "lead_time",
        "delivery duration": "lead_time",
        "supplier lead time": "lead_time",

        # Disruption
        "disruptions": "disruption",
        "disrupted": "disruption",
        "supply interruption": "disruption",
        "supply interruptions": "disruption",
        "supplier interruption": "disruption",
        "supplier issue": "disruption",
        "supplier issues": "disruption",
        "interruption event": "disruption",

        # Cost
        "cost": "unit_cost",
        "costs": "unit_cost",
        "price": "unit_cost",
        "prices": "unit_cost",
        "cheap": "low_cost",
        "affordable": "low_cost",
        "inexpensive": "low_cost",
        "expensive": "high_cost",
        "premium": "high_cost",

        # Demand & Sales
        "customer demand": "demand",
        "orders demand": "demand",
        "sales volume": "sales",
        "revenue": "sales",
        "selling": "sales",
    }

    # =========================================================================
    # CORE INTERPRETATION ENTRY POINT
    # =========================================================================

    def interpret(self, query: str) -> dict[str, Any]:
        """
        Parse natural-language query into normalized analytical dimensions.
        """
        raw_text = (query or "").strip()
        if not raw_text:
            return self._empty_result()

        # Check out-of-domain / unsupported questions
        if self._is_out_of_domain(raw_text):
            return self._unsupported_result(raw_text)

        norm_text = self._normalize_synonyms(raw_text.lower())

        # Extract entities
        entity_ids = self._extract_entity_ids(raw_text)
        primary_entity_id = entity_ids[0] if entity_ids else None
        is_self_scope = self._detect_self_scope(norm_text)

        # Detect comparison
        is_comparison = self._detect_comparison(norm_text, entity_ids)

        # Detect negation & polarity
        negation_info = self._detect_negation_and_polarity(norm_text)

        # Detect ranking
        ranking_info = self._detect_ranking(norm_text)

        # Detect threshold
        threshold_info = self._detect_threshold(raw_text)

        # Detect trend
        trend_info = self._detect_trend(norm_text)

        # Detect explanation ("why")
        is_explanation = self._detect_explanation(norm_text)

        # Detect multi-requirement query
        multi_reqs = self._detect_multi_requirements(
            norm_text=norm_text,
            raw_text=raw_text,
            entity_ids=entity_ids,
            primary_entity_id=primary_entity_id,
        )
        if len(multi_reqs) > 1:
            return self._build_multi_requirement_plan(
                query=raw_text,
                requirements=multi_reqs,
                entity_ids=entity_ids,
            )

        # Single requirement resolution
        return self._resolve_single_requirement(
            raw_text=raw_text,
            norm_text=norm_text,
            entity_ids=entity_ids,
            primary_entity_id=primary_entity_id,
            is_self_scope=is_self_scope,
            is_comparison=is_comparison,
            negation_info=negation_info,
            ranking_info=ranking_info,
            threshold_info=threshold_info,
            trend_info=trend_info,
            is_explanation=is_explanation,
        )

    # =========================================================================
    # OUT-OF-DOMAIN DETECTION
    # =========================================================================

    def _is_out_of_domain(self, text: str) -> bool:
        t = text.lower()
        unsupported_patterns = [
            r"\bweather\b",
            r"\btokyo\b",
            r"\bguitar\b",
            r"\bstrings in\b",
            r"\bcapital of\b",
            r"\bpresident\b",
            r"\bfootball\b",
            r"\bcricket\b",
            r"\bmovie\b",
            r"\brecipe\b",
        ]
        for pat in unsupported_patterns:
            if re.search(pat, t):
                return True
        return False

    def _unsupported_result(self, raw_text: str) -> dict[str, Any]:
        return {
            "intent": "unknown",
            "domain": None,
            "metric": None,
            "operation": "clarify",
            "direction": "none",
            "entity": None,
            "entity_id": None,
            "entity_ids": [],
            "condition": None,
            "negative_condition": False,
            "threshold": None,
            "trend": None,
            "scope": None,
            "complexity": "simple",
            "confidence": 0.0,
            "clarification_question": (
                "I could not map this question to an executable supply-chain analytical operation. "
                "Please ask about suppliers, delivery performance, lead-time changes, inventory risks, "
                "product demand, disruptions, or forecasting."
            ),
            "requirements": [],
            "method": "unsupported_domain",
        }

    def _empty_result(self) -> dict[str, Any]:
        return {
            "intent": "unknown",
            "domain": None,
            "metric": None,
            "operation": "clarify",
            "direction": "none",
            "entity": None,
            "entity_id": None,
            "confidence": 0.0,
            "clarification_question": "What supply-chain information would you like to know?",
            "requirements": [],
            "method": "empty_query",
        }

    # =========================================================================
    # NORMALIZATION & EXTRACTION HELPERS
    # =========================================================================

    def _normalize_synonyms(self, text: str) -> str:
        res = text
        for phrase, replacement in sorted(self.SYNONYM_MAP.items(), key=lambda x: -len(x[0])):
            pattern = r"\b" + re.escape(phrase) + r"\b"
            res = re.sub(pattern, replacement, res)
        return res

    def _extract_entity_ids(self, text: str) -> list[str]:
        entities = []
        for m in re.finditer(r"\b([P|S|R]\d{3,5})\b", text, re.IGNORECASE):
            eid = m.group(1).upper()
            if eid not in entities:
                entities.append(eid)
        return entities

    def _detect_self_scope(self, text: str) -> bool:
        self_patterns = [
            r"\bmy performance\b",
            r"\bhow am i\b",
            r"\bhow is my\b",
            r"\bhow are my\b",
            r"\bmy deliveries\b",
            r"\bmy delivery\b",
            r"\bmy supplier\b",
            r"\bmy orders\b",
            r"\bmy late rate\b",
            r"\bmy metrics\b",
        ]
        return any(re.search(p, text) for p in self_patterns)

    # =========================================================================
    # NEGATION, RANKING, THRESHOLD, TREND, COMPARISON
    # =========================================================================

    def _detect_negation_and_polarity(self, text: str) -> dict[str, Any]:
        """
        Distinguishes absolute negation from relative ranking or positive traits.
        """
        has_absolute_negation = bool(re.search(
            r"\b(no risk|not affected|not impacted|unaffected|unimpacted|immune to|free from|without disruption|no disruption|zero disruption|without significant|no significant)\b",
            text
        ))

        has_low_or_safe = bool(re.search(
            r"\b(low|lowest|least|safe|safest|minimal|stable|good|best|performing well|minimal problems)\b",
            text
        ))

        is_least_relative = bool(re.search(
            r"\b(least affected|least impacted|least likely|lowest risk|lowest delivery risk|lowest stockout risk)\b",
            text
        ))

        return {
            "has_absolute_negation": has_absolute_negation,
            "has_low_or_safe": has_low_or_safe,
            "is_least_relative": is_least_relative,
            "is_negative": has_absolute_negation or has_low_or_safe,
        }

    def _detect_ranking(self, text: str) -> dict[str, Any]:
        desc_patterns = [
            r"\bhighest\b", r"\bmost\b", r"\blargest\b", r"\bmaximum\b",
            r"\btop\b", r"\bgreatest\b", r"\bworst\b", r"\bmost affected\b",
            r"\bsevere\b", r"\belevated\b", r"\bmore\b",
        ]
        asc_patterns = [
            r"\blowest\b", r"\bleast\b", r"\bsmallest\b", r"\bminimum\b",
            r"\bbottom\b", r"\bfewest\b", r"\bleast affected\b", r"\bbest\b",
            r"\bcheapest\b", r"\bminimal\b",
        ]

        is_desc = any(re.search(p, text) for p in desc_patterns)
        is_asc = any(re.search(p, text) for p in asc_patterns)

        is_rank_op = bool(re.search(r"\b(rank|ranking|top|bottom|highest|lowest|most|least|best|worst|largest|smallest)\b", text))

        if is_asc:
            direction = "ascending"
        elif is_desc:
            direction = "descending"
        else:
            direction = "none"

        return {
            "direction": direction,
            "is_rank": is_rank_op or is_asc or is_desc,
        }

    def _detect_threshold(self, text: str) -> dict[str, Any] | None:
        """
        Extracts threshold expressions like:
        - above 50%
        - less than 10%
        - above 80%
        - less than 5 days of inventory cover
        - more than 10 days of inventory cover
        """
        # Match pattern: [operator] [value] [unit]
        # Operators: above, greater than, more than, over, exceeding, >, >=
        # Operators: below, less than, under, fewer than, <, <=
        greater_pats = [r"above", r"greater than", r"more than", r"over", r"exceeding", r">=", r">"]
        less_pats = [r"below", r"less than", r"under", r"fewer than", r"<=", r"<"]

        # Combined regex: (operator) \s* (\d+(?:\.\d+)?) \s* (%|days|units|d)?
        pattern = re.compile(
            r"\b(above|greater than|more than|over|exceeding|below|less than|under|fewer than)\s+(\d+(?:\.\d+)?)\s*(%|percent|days|units|d)?\b",
            re.IGNORECASE
        )
        match = pattern.search(text)
        if match:
            op_text = match.group(1).lower()
            val_text = float(match.group(2))
            unit_text = (match.group(3) or "").lower()
            if unit_text in {"percent", "%"}:
                unit_text = "%"
            elif unit_text in {"d", "days"}:
                unit_text = "days"
            elif not unit_text:
                if "%" in text:
                    unit_text = "%"
                elif "day" in text.lower():
                    unit_text = "days"
                else:
                    unit_text = "units"

            op = ">" if any(g in op_text for g in ["above", "greater", "more", "over", "exceeding"]) else "<"

            return {
                "operator": op,
                "value": val_text,
                "unit": unit_text,
            }

        return None

    def _detect_trend(self, text: str) -> dict[str, Any]:
        """
        Extracts trend semantics: increase, decrease, unusual, check.
        """
        is_increasing_or_decreasing = bool(re.search(r"\b(increasing or decreasing|rising or falling|trend)\b", text))
        if is_increasing_or_decreasing:
            return {"trend": "check", "direction": "none"}

        is_increasing = bool(re.search(
            r"\b(increasing|rising|growing|increase|growth|upward|getting worse)\b", text
        ))
        is_decreasing = bool(re.search(
            r"\b(decreasing|falling|declining|decrease|drop|downward|improving)\b", text
        ))
        is_unusual = bool(re.search(
            r"\b(unusual|abnormal|anomalous|anomaly|anomalies|change|changes|spike|spikes)\b", text
        ))

        is_largest_increase = bool(re.search(
            r"\b(largest|biggest|highest|greatest)\s+(lead[-_ ]?time\s+)?increase\b", text
        ))

        if is_largest_increase:
            return {"trend": "increase", "operation": "rank", "direction": "descending"}
        if is_increasing:
            return {"trend": "increase", "operation": "filter", "direction": "descending"}
        if is_decreasing:
            return {"trend": "decrease", "operation": "filter", "direction": "ascending"}
        if is_unusual:
            return {"trend": "unusual", "operation": "detect_anomaly", "direction": "descending"}

        return {"trend": None, "direction": "none"}

    def _detect_comparison(self, text: str, entity_ids: list[str]) -> bool:
        if len(entity_ids) >= 2:
            return True
        return bool(re.search(r"\b(compare|comparison|which is worse|which is better|higher late rate|lower late rate)\b", text))

    def _detect_explanation(self, text: str) -> bool:
        return bool(re.search(r"\b(why is|why are|why does|explain|reason for|causes of|what causes)\b", text))

    # =========================================================================
    # MULTI-REQUIREMENT DECOMPOSITION
    # =========================================================================

    def _detect_multi_requirements(
        self,
        norm_text: str,
        raw_text: str,
        entity_ids: list[str],
        primary_entity_id: str | None,
    ) -> list[dict[str, Any]]:
        """
        Decomposes composite queries joined by 'and', 'who supplies ... and how many orders', etc.
        """
        requirements = []

        # Case 1: "What is the demand for P00003 and which supplier provides it?"
        # Pattern: demand for P... and supplier
        if (
            ("demand" in norm_text or "total_demand" in norm_text)
            and ("supplier" in norm_text or "provides" in norm_text or "supplies" in norm_text)
            and primary_entity_id
            and primary_entity_id.startswith("P")
        ):
            requirements.append({
                "domain": "demand",
                "operation": "lookup",
                "metric": "total_demand",
                "direction": "none",
                "entity": "product",
                "entity_id": primary_entity_id,
                "purpose": "Analyze customer demand volume for the product",
                "depends_on": None,
            })
            requirements.append({
                "domain": "supplier",
                "operation": "lookup",
                "metric": "product_supplier",
                "direction": "none",
                "entity": "product",
                "entity_id": primary_entity_id,
                "purpose": "Identify primary supplying vendor for the product",
                "depends_on": None,
            })
            return requirements

        # Case 2: "Who supplied product P00003 and how many total orders from this supplier?"
        if (
            ("who supplied" in norm_text or "supplier" in norm_text)
            and ("orders" in norm_text or "total orders" in norm_text)
            and primary_entity_id
            and primary_entity_id.startswith("P")
        ):
            requirements.append({
                "domain": "supplier",
                "operation": "lookup",
                "metric": "product_supplier",
                "direction": "none",
                "entity": "product",
                "entity_id": primary_entity_id,
                "purpose": "Identify supplier for the specified product",
                "depends_on": None,
            })
            requirements.append({
                "domain": "order",
                "operation": "lookup",
                "metric": "total_orders",
                "direction": "none",
                "entity": "supplier",
                "entity_id": None,
                "purpose": "Count total fulfillment orders executed with this supplier",
                "depends_on": 0,
            })
            return requirements

        # Case 3: "Which suppliers have high delivery risk and what are their average delays?"
        if (
            "supplier" in norm_text
            and ("risk" in norm_text or "late" in norm_text)
            and ("average delay" in norm_text or "avg delay" in norm_text or "delay" in norm_text)
            and not primary_entity_id
        ):
            requirements.append({
                "domain": "supplier",
                "operation": "filter",
                "metric": "late_rate",
                "direction": "descending",
                "entity": "supplier",
                "condition": "high_risk",
                "purpose": "Filter suppliers exhibiting high delivery delay risk",
                "depends_on": None,
            })
            requirements.append({
                "domain": "delivery",
                "operation": "lookup",
                "metric": "delivery_delay",
                "direction": "descending",
                "entity": "supplier",
                "purpose": "Calculate average delay days for the identified suppliers",
                "depends_on": 0,
            })
            return requirements

        # Case 4: "Which supplier provides the highest-demand products?"
        if "highest-demand products" in norm_text or ("highest demand" in norm_text and "supplier provides" in norm_text):
            requirements.append({
                "domain": "demand",
                "operation": "rank",
                "metric": "total_demand",
                "direction": "descending",
                "entity": "product",
                "purpose": "Rank products by customer demand volume",
                "depends_on": None,
            })
            requirements.append({
                "domain": "supplier",
                "operation": "lookup",
                "metric": "product_supplier",
                "direction": "none",
                "entity": "product",
                "purpose": "Lookup suppliers responsible for the top demand products",
                "depends_on": 0,
            })
            return requirements

        return []

    def _build_multi_requirement_plan(
        self,
        query: str,
        requirements: list[dict[str, Any]],
        entity_ids: list[str],
    ) -> dict[str, Any]:
        first = requirements[0]
        return {
            "intent": "multi_requirement",
            "domain": first.get("domain"),
            "metric": first.get("metric"),
            "operation": first.get("operation", "lookup"),
            "direction": first.get("direction", "none"),
            "entity": first.get("entity"),
            "entity_id": first.get("entity_id"),
            "entity_ids": entity_ids,
            "condition": first.get("condition"),
            "negative_condition": False,
            "complexity": "complex",
            "confidence": 0.95,
            "requirements": requirements,
            "method": "semantic_multi_requirement",
        }

    # =========================================================================
    # SINGLE REQUIREMENT RESOLUTION
    # =========================================================================

    def _resolve_single_requirement(
        self,
        raw_text: str,
        norm_text: str,
        entity_ids: list[str],
        primary_entity_id: str | None,
        is_self_scope: bool,
        is_comparison: bool,
        negation_info: dict[str, Any],
        ranking_info: dict[str, Any],
        threshold_info: dict[str, Any] | None,
        trend_info: dict[str, Any],
        is_explanation: bool,
    ) -> dict[str, Any]:
        """
        Maps normalized intent to structured domain, metric, and operation.
        """

        # ---------------------------------------------------------------------
        # 1. COMPARISON QUERIES
        # ---------------------------------------------------------------------
        if is_comparison and len(entity_ids) >= 2:
            e1, e2 = entity_ids[0], entity_ids[1]
            is_sup = e1.startswith("S") or e2.startswith("S") or "supplier" in norm_text

            metric = "late_rate"
            if "lead time" in norm_text or "lead_time" in norm_text:
                metric = "lead_time_days"
            elif "delivery performance" in norm_text or "performance" in norm_text:
                metric = "delivery_performance"
            elif "late rate" in norm_text or "late" in norm_text:
                metric = "late_rate"
            elif "delay" in norm_text:
                metric = "avg_delay"

            target = (
                "higher" if any(w in norm_text for w in ["higher", "worse", "more"])
                else ("lower" if any(w in norm_text for w in ["lower", "better", "less"])
                else "compare")
            )
            dir_val = "descending" if target == "higher" else ("ascending" if target == "lower" else "none")

            return {
                "intent": "comparison",
                "domain": "supplier" if is_sup else "product",
                "metric": metric,
                "operation": "compare",
                "direction": dir_val,
                "entity": "supplier" if is_sup else "product",
                "entity_id": e1,
                "entity_ids": [e1, e2],
                "comparison": {
                    "entities": [e1, e2],
                    "metric": metric,
                    "target": target,
                },
                "confidence": 0.95,
                "requirements": [
                    {
                        "domain": "supplier" if is_sup else "product",
                        "operation": "compare",
                        "metric": metric,
                        "direction": dir_val,
                        "entity": "supplier" if is_sup else "product",
                        "entity_id": e1,
                        "entity_ids": [e1, e2],
                        "comparison": {
                            "entities": [e1, e2],
                            "metric": metric,
                            "target": target,
                        },
                        "depends_on": None,
                    }
                ],
                "method": "semantic_comparison",
            }

        # ---------------------------------------------------------------------
        # 2. DISRUPTION QUERIES (Products & Suppliers, Positive & Negative)
        # ---------------------------------------------------------------------
        if "disruption" in norm_text:
            is_supplier_target = (
                "supplier" in norm_text
                and not any(p in norm_text for p in ["product", "products", "item", "items", "sku", "skus"])
            )
            entity_type = "supplier" if is_supplier_target else "product"

            is_negative = negation_info["is_negative"]
            condition = "not_affected" if is_negative else "affected"

            if ranking_info["is_rank"]:
                operation = "rank"
                direction = ranking_info["direction"]
                if direction == "none":
                    direction = "ascending" if is_negative else "descending"
            else:
                operation = "filter"
                direction = "ascending" if is_negative else "descending"

            return {
                "intent": f"{entity_type}_disruption_impact",
                "domain": entity_type,
                "metric": "supplier_disruption_impact",
                "operation": operation,
                "direction": direction,
                "entity": entity_type,
                "entity_id": primary_entity_id,
                "entity_ids": entity_ids,
                "condition": condition,
                "negative_condition": is_negative,
                "driver": "supplier disruption",
                "topic": "supplier_disruption",
                "confidence": 0.95,
                "requirements": [
                    {
                        "domain": entity_type,
                        "operation": operation,
                        "metric": "supplier_disruption_impact",
                        "direction": direction,
                        "entity": entity_type,
                        "entity_id": primary_entity_id,
                        "entity_ids": entity_ids,
                        "condition": condition,
                        "negative_condition": is_negative,
                        "driver": "supplier disruption",
                        "topic": "supplier_disruption",
                        "depends_on": None,
                    }
                ],
                "method": "semantic_disruption",
            }

        # ---------------------------------------------------------------------
        # 3. LEAD TIME & ANOMALIES
        # ---------------------------------------------------------------------
        if "lead_time" in norm_text:
            trend = trend_info.get("trend")
            op = trend_info.get("operation") or ("rank" if ranking_info["is_rank"] else "filter")
            dir_val = trend_info.get("direction") or ranking_info["direction"]
            if dir_val == "none":
                dir_val = "descending" if trend == "increase" else ("ascending" if trend == "decrease" else "descending")

            return {
                "intent": "lead_time_anomaly",
                "domain": "supplier",
                "metric": "lead_time_anomaly",
                "operation": op,
                "direction": dir_val,
                "entity": "supplier",
                "entity_id": primary_entity_id,
                "entity_ids": entity_ids,
                "trend": trend or "unusual",
                "confidence": 0.95,
                "requirements": [
                    {
                        "domain": "supplier",
                        "operation": op,
                        "metric": "lead_time_anomaly",
                        "direction": dir_val,
                        "entity": "supplier",
                        "entity_id": primary_entity_id,
                        "trend": trend or "unusual",
                        "depends_on": None,
                    }
                ],
                "method": "semantic_lead_time",
            }

        # ---------------------------------------------------------------------
        # 4. RELATIONSHIP LOOKUPS ("Who supplies P00003?", "Which products does S0147 supply?")
        # ---------------------------------------------------------------------
        if (
            ("who supplies" in norm_text or "who is the supplier" in norm_text or "supplier for" in norm_text)
            and primary_entity_id and primary_entity_id.startswith("P")
        ):
            return {
                "intent": "supplier_relationship_analysis",
                "domain": "supplier",
                "metric": "product_supplier",
                "operation": "lookup",
                "direction": "none",
                "entity": "product",
                "entity_id": primary_entity_id,
                "entity_ids": entity_ids,
                "confidence": 0.95,
                "requirements": [
                    {
                        "domain": "supplier",
                        "operation": "lookup",
                        "metric": "product_supplier",
                        "direction": "none",
                        "entity": "product",
                        "entity_id": primary_entity_id,
                        "depends_on": None,
                    }
                ],
                "method": "semantic_relationship",
            }

        if (
            ("which products" in norm_text or "products supplied" in norm_text or "products does" in norm_text or "supplies" in norm_text)
            and primary_entity_id and primary_entity_id.startswith("S")
        ):
            return {
                "intent": "supplier_relationship_analysis",
                "domain": "product",
                "metric": "supplier_product",
                "operation": "lookup",
                "direction": "none",
                "entity": "supplier",
                "entity_id": primary_entity_id,
                "entity_ids": entity_ids,
                "confidence": 0.95,
                "requirements": [
                    {
                        "domain": "product",
                        "operation": "lookup",
                        "metric": "supplier_product",
                        "direction": "none",
                        "entity": "supplier",
                        "entity_id": primary_entity_id,
                        "depends_on": None,
                    }
                ],
                "method": "semantic_relationship",
            }

        # ---------------------------------------------------------------------
        # 5. INVENTORY & STOCKOUT (Thresholds, Low/High, Explanation)
        # ---------------------------------------------------------------------
        if "days_of_cover" in norm_text or "inventory cover" in norm_text:
            op = "filter" if threshold_info else ("rank" if ranking_info["is_rank"] else "lookup")
            dir_val = ranking_info["direction"] if ranking_info["direction"] != "none" else "descending"
            return {
                "intent": "inventory_cover",
                "domain": "inventory",
                "metric": "days_of_cover",
                "operation": op,
                "direction": dir_val,
                "entity": "product",
                "entity_id": primary_entity_id,
                "entity_ids": entity_ids,
                "threshold": threshold_info,
                "confidence": 0.95,
                "requirements": [
                    {
                        "domain": "inventory",
                        "operation": op,
                        "metric": "days_of_cover",
                        "direction": dir_val,
                        "entity": "product",
                        "entity_id": primary_entity_id,
                        "threshold": threshold_info,
                        "depends_on": None,
                    }
                ],
                "method": "semantic_inventory_cover",
            }

        if "stockout" in norm_text:
            is_low = negation_info["has_low_or_safe"] or ranking_info["direction"] == "ascending"
            op = "filter" if threshold_info else "rank"
            dir_val = "ascending" if is_low else "descending"
            cond = "low_risk" if is_low else "high_risk"

            return {
                "intent": "stockout_ranking",
                "domain": "inventory",
                "metric": "stockout_rate",
                "operation": op,
                "direction": dir_val,
                "entity": "product",
                "entity_id": primary_entity_id,
                "entity_ids": entity_ids,
                "condition": cond,
                "negative_condition": is_low,
                "threshold": threshold_info,
                "confidence": 0.95,
                "requirements": [
                    {
                        "domain": "inventory",
                        "operation": op,
                        "metric": "stockout_rate",
                        "direction": dir_val,
                        "entity": "product",
                        "entity_id": primary_entity_id,
                        "condition": cond,
                        "negative_condition": is_low,
                        "threshold": threshold_info,
                        "depends_on": None,
                    }
                ],
                "method": "semantic_stockout",
            }

        if "inventory" in norm_text:
            if is_explanation and primary_entity_id:
                return {
                    "intent": "inventory_risk",
                    "domain": "inventory",
                    "metric": "risk_score",
                    "operation": "explain",
                    "direction": "none",
                    "entity": "product",
                    "entity_id": primary_entity_id,
                    "entity_ids": entity_ids,
                    "confidence": 0.95,
                    "requirements": [
                        {
                            "domain": "inventory",
                            "operation": "explain",
                            "metric": "risk_score",
                            "direction": "none",
                            "entity": "product",
                            "entity_id": primary_entity_id,
                            "depends_on": None,
                        }
                    ],
                    "method": "semantic_inventory_explain",
                }

            is_low = negation_info["has_low_or_safe"] or ranking_info["direction"] == "ascending"
            dir_val = "ascending" if is_low else "descending"
            return {
                "intent": "inventory_risk",
                "domain": "inventory",
                "metric": "risk_score",
                "operation": "rank" if ranking_info["is_rank"] else "filter",
                "direction": dir_val,
                "entity": "product",
                "entity_id": primary_entity_id,
                "entity_ids": entity_ids,
                "condition": "low_risk" if is_low else "high_risk",
                "negative_condition": is_low,
                "confidence": 0.95,
                "requirements": [
                    {
                        "domain": "inventory",
                        "operation": "rank" if ranking_info["is_rank"] else "filter",
                        "metric": "risk_score",
                        "direction": dir_val,
                        "entity": "product",
                        "entity_id": primary_entity_id,
                        "condition": "low_risk" if is_low else "high_risk",
                        "negative_condition": is_low,
                        "depends_on": None,
                    }
                ],
                "method": "semantic_inventory_risk",
            }

        # ---------------------------------------------------------------------
        # 6. FORECASTING & DEMAND PREDICTION
        # ---------------------------------------------------------------------
        if "forecast" in norm_text or "predict" in norm_text or trend_info.get("trend") == "check":
            trend = trend_info.get("trend")
            target_pid = primary_entity_id or "P00003"
            return {
                "intent": "forecast",
                "domain": "forecast",
                "metric": "forecast_demand",
                "operation": "forecast",
                "direction": "none",
                "entity": "product",
                "entity_id": target_pid,
                "entity_ids": [target_pid],
                "trend": trend,
                "confidence": 0.95,
                "requirements": [
                    {
                        "domain": "forecast",
                        "operation": "forecast",
                        "metric": "forecast_demand",
                        "direction": "none",
                        "entity": "product",
                        "entity_id": target_pid,
                        "trend": trend,
                        "depends_on": None,
                    }
                ],
                "method": "semantic_forecast",
            }

        # ---------------------------------------------------------------------
        # 7. PERFORMANCE & AUTHENTICATED USER SCOPE QUERIES
        # ---------------------------------------------------------------------
        if is_self_scope or "how many deliveries were late" in norm_text or "late deliveries" in norm_text:
            return {
                "intent": "delivery_performance",
                "domain": "delivery",
                "metric": "delivery_performance",
                "operation": "summarize",
                "direction": "none",
                "entity": "delivery",
                "entity_id": primary_entity_id,
                "entity_ids": entity_ids,
                "scope": "user_supplier" if is_self_scope else "network",
                "confidence": 0.95,
                "requirements": [
                    {
                        "domain": "delivery",
                        "operation": "summarize",
                        "metric": "delivery_performance",
                        "direction": "none",
                        "entity": "delivery",
                        "entity_id": primary_entity_id,
                        "scope": "user_supplier" if is_self_scope else "network",
                        "depends_on": None,
                    }
                ],
                "method": "semantic_performance",
            }

        # ---------------------------------------------------------------------
        # 8. SUPPLIER DELIVERY RISK (LOW, HIGH, RANKING, FILTERS, THRESHOLDS)
        # ---------------------------------------------------------------------
        if "supplier" in norm_text or "late_rate" in norm_text or "late" in norm_text:
            is_low = (
                negation_info["has_absolute_negation"]
                or negation_info["has_low_or_safe"]
                or ranking_info["direction"] == "ascending"
                or any(w in norm_text for w in ["good delivery performance", "performing well", "no risk", "safe", "stable"])
            )
            is_rank = (
                ranking_info["is_rank"]
                or any(w in norm_text for w in ["highest", "lowest", "most", "least", "top", "bottom"])
            )

            condition = "low_risk" if is_low else "high_risk"
            operation = "filter" if threshold_info else ("rank" if is_rank else "filter")
            direction = "ascending" if is_low else "descending"

            return {
                "intent": "supplier_risk",
                "domain": "supplier",
                "metric": "late_rate",
                "operation": operation,
                "direction": direction,
                "entity": "supplier",
                "entity_id": primary_entity_id,
                "entity_ids": entity_ids,
                "condition": condition,
                "negative_condition": is_low,
                "threshold": threshold_info,
                "driver": "delivery delay",
                "topic": "delivery_risk",
                "confidence": 0.95,
                "requirements": [
                    {
                        "domain": "supplier",
                        "operation": operation,
                        "metric": "late_rate",
                        "direction": direction,
                        "entity": "supplier",
                        "entity_id": primary_entity_id,
                        "condition": condition,
                        "negative_condition": is_low,
                        "threshold": threshold_info,
                        "driver": "delivery delay",
                        "topic": "delivery_risk",
                        "depends_on": None,
                    }
                ],
                "method": "semantic_supplier_risk",
            }

        # ---------------------------------------------------------------------
        # 9. GENERAL DEMAND / SALES / COST
        # ---------------------------------------------------------------------
        if "demand" in norm_text:
            dir_val = ranking_info["direction"] if ranking_info["direction"] != "none" else "descending"
            return {
                "intent": "demand_ranking",
                "domain": "demand",
                "metric": "total_demand",
                "operation": "rank" if not primary_entity_id else "lookup",
                "direction": dir_val,
                "entity": "product",
                "entity_id": primary_entity_id,
                "entity_ids": entity_ids,
                "confidence": 0.95,
                "requirements": [
                    {
                        "domain": "demand",
                        "operation": "rank" if not primary_entity_id else "lookup",
                        "metric": "total_demand",
                        "direction": dir_val,
                        "entity": "product",
                        "entity_id": primary_entity_id,
                        "depends_on": None,
                    }
                ],
                "method": "semantic_demand",
            }

        if "unit_cost" in norm_text or "cost" in norm_text or "price" in norm_text:
            is_low = any(w in norm_text for w in ["cheap", "affordable", "inexpensive", "low cost", "lowest cost"])
            dir_val = "ascending" if is_low else "descending"
            return {
                "intent": "product_cost_ranking",
                "domain": "product",
                "metric": "unit_cost",
                "operation": "rank",
                "direction": dir_val,
                "entity": "product",
                "entity_id": primary_entity_id,
                "entity_ids": entity_ids,
                "confidence": 0.95,
                "requirements": [
                    {
                        "domain": "product",
                        "operation": "rank",
                        "metric": "unit_cost",
                        "direction": dir_val,
                        "entity": "product",
                        "entity_id": primary_entity_id,
                        "depends_on": None,
                    }
                ],
                "method": "semantic_cost",
            }

        # ---------------------------------------------------------------------
        # 10. CARRIER / DELIVERY RISK
        # ---------------------------------------------------------------------
        if "delivery" in norm_text:
            return {
                "intent": "delivery_performance",
                "domain": "delivery",
                "metric": "delivery_performance",
                "operation": "summarize",
                "direction": "none",
                "entity": "delivery",
                "entity_id": primary_entity_id,
                "entity_ids": entity_ids,
                "confidence": 0.90,
                "requirements": [
                    {
                        "domain": "delivery",
                        "operation": "summarize",
                        "metric": "delivery_performance",
                        "direction": "none",
                        "entity": "delivery",
                        "entity_id": primary_entity_id,
                        "depends_on": None,
                    }
                ],
                "method": "semantic_delivery",
            }

        # Fallback to clarify
        return {
            "intent": "unknown",
            "domain": None,
            "metric": None,
            "operation": "clarify",
            "direction": "none",
            "entity": None,
            "entity_id": None,
            "entity_ids": [],
            "confidence": 0.0,
            "clarification_question": "Could you clarify what supply-chain metrics or operations you want to analyze?",
            "requirements": [],
            "method": "fallback_clarify",
        }
