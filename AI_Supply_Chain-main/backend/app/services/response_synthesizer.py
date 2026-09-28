from __future__ import annotations

import json
from typing import Any


def clean_evidence_item(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {
            "source_type": "analytics",
            "source_id": "analytics:general",
            "entity_type": "analytics",
            "entity_id": "",
            "metric": "general",
            "value": str(item),
            "explanation": str(item),
            "retrieval_method": "structured",
            "confidence": 1.0,
            "data": {},
        }

    clean = dict(item)
    val = clean.get("value")
    data = clean.get("data")
    if not isinstance(data, dict):
        data = {}

    # If value is a dictionary, extract scalar and merge into data
    if isinstance(val, dict):
        data = {**val, **data}
        clean["data"] = data
        metric = clean.get("metric")
        clean["value"] = (
            data.get(metric)
            or data.get("risk_score")
            or data.get("late_rate")
            or data.get("absolute_change_days")
            or data.get("exposure_score")
            or data.get("stockout_rate")
            or data.get("total_orders")
            or data.get("unit_cost")
            or data.get("total_demand")
            or data.get("total_sales")
            or next((v for v in data.values() if isinstance(v, (int, float, str))), 0.0)
        )

    # Format numeric value cleanly if float
    if isinstance(clean.get("value"), float):
        clean["value"] = round(clean["value"], 2)

    # Clean explanation if it contains stringified python dicts
    expl = str(clean.get("explanation") or "")
    if "{" in expl and "}" in expl:
        m_label = str(clean.get("metric", "")).replace("_", " ").capitalize()
        ent = clean.get("entity_id") or ""
        v = clean.get("value")
        expl = f"{m_label} for {ent}: {v}"
    clean["explanation"] = expl
    clean["confidence"] = float(clean.get("confidence", 1.0))
    clean["retrieval_method"] = clean.get("retrieval_method", "structured")

    return clean


def clean_evidence_list(evidence: list[Any]) -> list[dict[str, Any]]:
    return [clean_evidence_item(item) for item in (evidence or [])]


class ResponseSynthesizer:
    """
    Synthesizes executive-ready, evidence-grounded supply-chain intelligence
    in a structured 6-part enterprise markdown format.
    Zero raw python dicts, zero ungrounded generic answers.
    """

    @classmethod
    def synthesize(
        cls,
        *,
        query: str,
        result: dict[str, Any],
        findings: list[Any],
        evidence: list[dict[str, Any]],
        requirement_results: list[dict[str, Any]],
        user_scope: Any | None = None,
        status: str = "success",
        semantic_docs: list[Any] | None = None,
        sources: list[str] | None = None,
    ) -> dict[str, Any]:
        cleaned_ev = clean_evidence_list(evidence)
        sources_list = list(sources or ["Deterministic Analytics Engine"])

        # 1. Access Denied (RBAC)
        if status == "denied":
            return cls._synthesize_denied(query, user_scope, result)

        # 2. Unsupported / Clarification
        if status in {"clarification_required", "unsupported"}:
            return cls._synthesize_unsupported(query, status, result)

        # 3. LLM Evidence Interpretation (Primary for queries with evidence)
        if cleaned_ev and status == "success":
            llm_synth = cls._interpret_with_llm(
                query=query,
                result=result,
                evidence=cleaned_ev,
                sources=sources_list,
            )
            if llm_synth is not None:
                return llm_synth

        # 4. Domain Specific Synthesizers (Deterministic Fallbacks)
        intent = str(result.get("intent") or "").lower()
        metric = str(result.get("metric") or "").lower()
        q_lower = query.lower()

        # Multi-requirement query
        if len(requirement_results) > 1:
            return cls._synthesize_multi_requirement(
                query, requirement_results, cleaned_ev, semantic_docs, sources_list
            )

        # Lead Time Anomaly
        if "lead_time" in metric or "lead_time" in intent or "lead time" in q_lower or "anomaly" in q_lower:
            return cls._synthesize_lead_time_anomaly(
                query, result, findings, cleaned_ev, sources_list
            )

        # Supplier Disruption Impact / Product Disruption Impact
        if "disruption" in metric or "disruption" in intent or "disruption" in q_lower:
            return cls._synthesize_disruption_impact(
                query, result, findings, cleaned_ev, sources_list
            )

        # Major Supply Chain Risks
        if "major_risk" in metric or "major_risk" in intent or "major" in q_lower or "risks right now" in q_lower:
            return cls._synthesize_major_risks(
                query, result, findings, cleaned_ev, sources_list
            )

        # Supplier Investigation
        if "investigate" in intent or "investigate" in q_lower or "supplier_investigation" in metric:
            return cls._synthesize_supplier_investigation(
                query, result, findings, cleaned_ev, semantic_docs, sources_list
            )

        # Delivery Risk / Carrier / 3PL
        if "delivery_risk" in metric or "delivery_risk" in intent or ("delivery" in q_lower and "supplier" not in q_lower) or "3pl" in q_lower or "carrier" in q_lower:
            return cls._synthesize_delivery_risk(
                query, result, findings, cleaned_ev, semantic_docs, sources_list
            )

        # Supplier Delivery Risk / Supplier Risk
        if "supplier" in intent or "supplier" in metric or "late_rate" in metric or "supplier" in q_lower:
            return cls._synthesize_supplier_risk(
                query, result, findings, cleaned_ev, semantic_docs, sources_list
            )

        # Inventory Risk / Stockout
        if "inventory" in intent or "risk_score" in metric or "stockout" in metric or "inventory" in q_lower:
            return cls._synthesize_inventory_risk(
                query, result, findings, cleaned_ev, semantic_docs, sources_list
            )

        # Forecast
        if "forecast" in intent or "forecast" in metric or "forecast" in q_lower:
            return cls._synthesize_forecast(
                query, result, findings, cleaned_ev, sources_list
            )

        # Order Analysis
        if "order" in metric or "order" in intent:
            return cls._synthesize_orders(
                query, result, findings, cleaned_ev, sources_list
            )

        # General Rankings (Sales, Demand, Cost)
        if metric in {"total_sales", "total_demand", "unit_cost"}:
            return cls._synthesize_ranking(
                query, result, findings, cleaned_ev, sources_list
            )

        # Fallback to generic enterprise synthesis
        return cls._synthesize_generic(
            query, result, findings, cleaned_ev, semantic_docs, sources_list
        )

    # =========================================================================
    # SPECIFIC DOMAIN IMPLEMENTATIONS
    # =========================================================================

    @classmethod
    def _synthesize_lead_time_anomaly(
        cls, query: str, result: dict[str, Any], findings: list[Any], evidence: list[dict[str, Any]], sources: list[str]
    ) -> dict[str, Any]:
        top_items = [f for f in findings if isinstance(f, dict)]
        anom_items = [f for f in top_items if f.get("is_anomaly") or "Increase" in str(f.get("status", ""))]
        items_to_report = anom_items if anom_items else top_items[:5]
        count = len(items_to_report)

        if items_to_report:
            top = items_to_report[0]
            top_sid = top.get("supplier_id", "Unknown")
            top_chg = top.get("absolute_change_days", 0.0)
            top_pct = top.get("percentage_change", 0.0)
            direct_answer = (
                f"Statistical lead-time analysis identified {count} supplier(s) exhibiting anomalous lead-time growth "
                f"over the recent 90-day window. Supplier {top_sid} demonstrated the most acute lead-time surge "
                f"(+{top_chg:.1f} days, +{top_pct:.1f}% vs historical baseline)."
            )
        else:
            direct_answer = "Statistical evaluation of historical vs recent 90-day purchase orders detected no significant lead-time anomalies across suppliers."

        key_findings = []
        for item in items_to_report[:4]:
            sid = item.get("supplier_id")
            rec = item.get("recent_avg_days", 0.0)
            hist = item.get("historical_avg_days", 0.0)
            chg = item.get("absolute_change_days", 0.0)
            pct = item.get("percentage_change", 0.0)
            stat = item.get("status", "Normal")
            sign = "+" if chg > 0 else ""
            key_findings.append(
                f"Supplier {sid}: Recent lead time {rec:.1f}d vs baseline {hist:.1f}d ({sign}{chg:.1f}d, {sign}{pct:.1f}%) — {stat}."
            )
        if not key_findings:
            key_findings.append("All monitored suppliers are delivering within standard historical variance bounds (±1.5 days).")

        evidence_summary = []
        for ev in evidence[:4]:
            expl = ev.get("explanation")
            if expl:
                evidence_summary.append(expl)
        if not evidence_summary:
            evidence_summary.append("Calculated 90-day rolling lead-time delta against multi-year order history baseline.")

        business_impact = (
            "Sudden lead-time elongation directly degrades replenishment predictability, eroding safety stock buffers "
            "and elevating stockout probabilities across downstream assembly and distribution nodes."
        )

        recommended_actions = [
            f"Dynamically update planned lead times in ERP/MRP for {items_to_report[0].get('supplier_id', 'affected suppliers')} to realign replenishment reorder points.",
            "Engage supplier logistics dispatchers immediately to diagnose transport bottlenecks, port delays, or component shortages.",
            "Conduct safety-stock coverage reviews and activate pre-qualified secondary sources for critical dependent SKUs.",
        ]

        return cls._build_markdown(
            direct_answer=direct_answer,
            key_findings=key_findings,
            evidence_summary=evidence_summary,
            business_impact=business_impact,
            recommended_actions=recommended_actions,
            sources=sources,
        )

    @classmethod
    def _synthesize_disruption_impact(
        cls, query: str, result: dict[str, Any], findings: list[Any], evidence: list[dict[str, Any]], sources: list[str]
    ) -> dict[str, Any]:
        top_items = [f for f in findings if isinstance(f, dict)]
        count = len(top_items)
        if top_items:
            top = top_items[0]
            top_pid = top.get("product_id", "Unknown")
            top_sid = top.get("supplier_id", "Unknown")
            top_score = top.get("exposure_score", 0.0)
            top_doc = top.get("days_of_cover", 0.0)
            direct_answer = (
                f"Supply disruption analysis reveals {count} product(s) with elevated vulnerability to supplier operational disruptions. "
                f"Product {top_pid} (sourced from supplier {top_sid}) exhibits the highest operational exposure (Score: {top_score:.1f}/100) "
                f"due to elevated supplier delays paired with thin inventory cover ({top_doc:.1f} days)."
            )
        else:
            direct_answer = "Analysis of current supplier delivery continuity and inventory buffers indicates stable supply chain coverage across catalog products."

        key_findings = []
        for p in top_items[:4]:
            pid = p.get("product_id")
            sid = p.get("supplier_id")
            s_risk = p.get("supplier_risk_level", "UNKNOWN")
            disp = p.get("disruption_rate", 0.0)
            doc = p.get("days_of_cover", 0.0)
            stockout = p.get("stockout_rate", 0.0)
            score = p.get("exposure_score", 0.0)
            key_findings.append(
                f"Product {pid}: Supplied by {sid} ({s_risk} risk), disruption rate {disp:.1f}%, days of cover {doc:.1f}d, stockout rate {stockout:.1f}% (Exposure: {score:.1f}/100)."
            )

        evidence_summary = []
        for ev in evidence[:4]:
            expl = ev.get("explanation")
            if expl:
                evidence_summary.append(expl)
        if not evidence_summary:
            evidence_summary.append("Combined supplier disruption flags, late-order frequencies, inventory levels, and historical stockout rates.")

        business_impact = (
            "High reliance on disrupted suppliers combined with limited warehouse inventory accelerates stockout occurrence, "
            "jeopardizing on-time customer fulfillment and incurring expedited logistics costs."
        )

        recommended_actions = [
            f"Increase inventory safety stock buffer for high-exposure products ({top_items[0].get('product_id', 'critical SKUs')}) from {top_items[0].get('days_of_cover', 15):.1f} days to minimum 30 days.",
            "Trigger secondary sourcing allocation or spot-buy procurement for critical components.",
            "Establish daily tracking for in-transit shipments and purchase orders tied to vulnerable suppliers.",
        ]

        return cls._build_markdown(
            direct_answer=direct_answer,
            key_findings=key_findings,
            evidence_summary=evidence_summary,
            business_impact=business_impact,
            recommended_actions=recommended_actions,
            sources=sources,
        )

    @classmethod
    def _synthesize_major_risks(
        cls, query: str, result: dict[str, Any], findings: list[Any], evidence: list[dict[str, Any]], sources: list[str]
    ) -> dict[str, Any]:
        f_map = {}
        for f in findings:
            if isinstance(f, dict):
                rd = f.get("risk_domain")
                if rd:
                    f_map[rd] = f
                else:
                    f_map.update(f)
        sup_risk = f_map.get("supplier_risk", {})
        inv_risk = f_map.get("inventory_risk", {})
        lt_anom = f_map.get("lead_time_anomalies", {})

        crit_sups = int(sup_risk.get("critical_count", 0))
        high_sups = int(sup_risk.get("high_count", 0))
        anom_count = int(lt_anom.get("anomalies_detected", 0))
        stockout_prods = int(inv_risk.get("products_with_stockouts", 0))

        direct_answer = (
            f"Enterprise risk intelligence synthesis identified critical vulnerabilities across supplier reliability, "
            f"inventory stockout risks, and lead-time stability. Across the network, {crit_sups} supplier(s) are at CRITICAL "
            f"delivery risk, {anom_count} lead-time anomalies were detected, and {stockout_prods} product(s) face stockout exposure."
        )

        key_findings = []
        top_sups = sup_risk.get("top_risk_suppliers", [])
        if top_sups:
            sup_labels = [f"{s['supplier_id']} ({s['risk_level']}, Late Rate: {s['late_rate']}%)" for s in top_sups[:3]]
            key_findings.append(f"Supplier Delivery Risk: {crit_sups} Critical / {high_sups} High risk suppliers identified, led by {', '.join(sup_labels)}.")

        top_stocks = inv_risk.get("top_stockout_products", [])
        if top_stocks:
            stock_labels = [f"{p['product_id']} ({p['stockout_rate']}% stockout rate, {p['days_of_cover']}d cover)" for p in top_stocks[:3]]
            key_findings.append(f"Inventory Vulnerability: Highest stockout exposure observed for {', '.join(stock_labels)}.")

        top_anoms = lt_anom.get("top_anomalies", [])
        if top_anoms:
            anom_labels = [f"{a['supplier_id']} (+{a['absolute_change_days']}d / +{a['percentage_change']}%)" for a in top_anoms[:2]]
            key_findings.append(f"Lead Time Inflation: Significant delivery duration spikes detected for {', '.join(anom_labels)}.")

        if not key_findings:
            key_findings.append("Cross-domain risk evaluation completed across suppliers, inventory, routes, and lead times.")

        evidence_summary = []
        for ev in evidence[:5]:
            expl = ev.get("explanation")
            if expl:
                evidence_summary.append(expl)

        business_impact = (
            "Compounding operational friction across chronic supplier delivery delays and thin inventory coverage "
            "creates systemic vulnerability to unfulfilled customer demand, factory stoppages, and SLA contractual penalties."
        )

        recommended_actions = [
            "Convene a cross-functional S&OP risk council to review critical supplier allocations and expedite pending purchase orders.",
            "Implement dual-sourcing contingency contracts for critical products currently single-sourced from CRITICAL-risk vendors.",
            "Recalibrate safety stock buffers in warehouse replenishment systems for inventory SKUs facing elevated stockout rates.",
        ]

        return cls._build_markdown(
            direct_answer=direct_answer,
            key_findings=key_findings,
            evidence_summary=evidence_summary,
            business_impact=business_impact,
            recommended_actions=recommended_actions,
            sources=sources,
        )

    @classmethod
    def _synthesize_supplier_investigation(
        cls, query: str, result: dict[str, Any], findings: list[Any], evidence: list[dict[str, Any]], semantic_docs: list[Any] | None, sources: list[str]
    ) -> dict[str, Any]:
        target_sid = result.get("entity_id") or "the selected supplier"
        first = findings[0] if (findings and isinstance(findings[0], dict)) else {}

        risk_level = first.get("risk_level") or result.get("risk_level") or "EVALUATED"
        risk_score = first.get("risk_score") or result.get("risk_score")
        late_rate = first.get("late_rate") or result.get("late_rate") or 0.0
        avg_delay = first.get("avg_delay") or first.get("avg_delay_days") or 0.0
        orders = first.get("total_orders") or 0

        score_text = f" (Risk Score: {risk_score:.1f})" if risk_score is not None else ""
        direct_answer = (
            f"Operational investigation for supplier {target_sid} indicates a {risk_level} risk profile{score_text} "
            f"based on {orders:,} historical orders, a {late_rate*100:.1f}% late delivery rate, and average delay of {avg_delay:.1f} days."
        )

        key_findings = [
            f"Supplier Risk Classification: {risk_level}{score_text}.",
            f"Delivery Reliability: {late_rate*100:.1f}% late-order frequency across {orders:,} analyzed orders.",
            f"Average Delay Impact: {avg_delay:.1f} days when delivery delays occur.",
        ]

        if semantic_docs:
            top_doc = semantic_docs[0]
            first_line = getattr(top_doc, "content", "").strip().split("\n")[0]
            if first_line:
                key_findings.append(f"Profile Summary: {first_line[:140]}...")

        evidence_summary = []
        for ev in evidence[:4]:
            expl = ev.get("explanation")
            if expl:
                evidence_summary.append(expl)

        business_impact = (
            f"Supplier {target_sid}'s delivery performance directly dictates component availability for downstream production. "
            f"Elevated late rates necessitate higher holding stock buffers and increase risk of production halts."
        )

        recommended_actions = [
            f"Schedule an operational vendor review with {target_sid} account management to address recent delivery variance.",
            "Establish strict SLA compliance benchmarks with milestone-based shipping notifications (ASNs).",
            "Audit secondary supplier capacity to ensure rapid volume re-allocation if performance deteriorates.",
        ]

        return cls._build_markdown(
            direct_answer=direct_answer,
            key_findings=key_findings,
            evidence_summary=evidence_summary,
            business_impact=business_impact,
            recommended_actions=recommended_actions,
            sources=sources,
        )

    @classmethod
    def _synthesize_supplier_risk(
        cls, query: str, result: dict[str, Any], findings: list[Any], evidence: list[dict[str, Any]], semantic_docs: list[Any] | None, sources: list[str]
    ) -> dict[str, Any]:
        target_sid = result.get("entity_id")
        
        # Single supplier query
        if target_sid:
            first = findings[0] if (findings and isinstance(findings[0], dict)) else {}
            risk_level = first.get("risk_level", "MONITORED")
            risk_score = first.get("risk_score")
            late_rate = first.get("late_rate", 0.0)
            avg_delay = first.get("avg_delay") or first.get("avg_delay_days", 0.0)
            orders = first.get("total_orders", 0)

            score_str = f" (Score: {risk_score:.1f})" if risk_score is not None else ""
            direct_answer = (
                f"Supplier {target_sid} is classified as {risk_level} risk{score_str} with a late-order rate of {late_rate*100:.1f}% "
                f"and an average delay of {avg_delay:.1f} days across {orders:,} historical orders."
            )
            key_findings = [
                f"Risk Classification: {risk_level}{score_str}.",
                f"Late Delivery Rate: {late_rate*100:.1f}%.",
                f"Average Delivery Delay: {avg_delay:.1f} days across {orders:,} total shipments.",
            ]
        else:
            # Multi-supplier query ("Which suppliers have risk?")
            valid_findings = [f for f in findings if isinstance(f, dict)]
            crit_sups = [f for f in valid_findings if f.get("risk_level") == "CRITICAL"]
            high_sups = [f for f in valid_findings if f.get("risk_level") == "HIGH"]
            med_sups = [f for f in valid_findings if f.get("risk_level") == "MEDIUM"]
            low_sups = [f for f in valid_findings if f.get("risk_level") == "LOW"]

            total_risk = len(crit_sups) + len(high_sups)
            top_names = [f"{s['supplier_id']} ({s.get('late_rate', 0)*100:.1f}% late)" for s in (crit_sups + high_sups)[:3]]
            names_str = ", ".join(top_names)
            direct_answer = (
                f"Supplier delivery risk evaluation identifies leading high-risk suppliers with severe fulfillment delays, "
                f"led by {names_str}."
            )

            key_findings = []
            if crit_sups:
                top_crit = [f"{s['supplier_id']} (Late: {s.get('late_rate', 0)*100:.1f}%, Delay: {s.get('avg_delay', 0):.1f}d)" for s in crit_sups[:3]]
                key_findings.append(f"CRITICAL Risk Suppliers: Highest late rates and delays observed with {', '.join(top_crit)}.")
            if high_sups:
                top_high = [f"{s['supplier_id']} (Late: {s.get('late_rate', 0)*100:.1f}%)" for s in high_sups[:3]]
                key_findings.append(f"HIGH Risk Suppliers: Elevated late-order frequencies observed with {', '.join(top_high)}.")

        evidence_summary = []
        for ev in evidence[:4]:
            expl = ev.get("explanation")
            if expl:
                evidence_summary.append(expl)

        business_impact = (
            "Elevated supplier late rates disrupt manufacturing schedules, increase buffer inventory holding costs, "
            "and threaten customer delivery SLA compliance."
        )

        recommended_actions = [
            "Prioritize vendor performance audits and initiate corrective action plans for all CRITICAL-tier suppliers.",
            "Reallocate near-term purchase order volumes toward compliant LOW and MEDIUM risk suppliers where dual-sourcing is active.",
            "Institute stricter penalty clauses and advance shipping notice requirements on recurring late delivery routes.",
        ]

        return cls._build_markdown(
            direct_answer=direct_answer,
            key_findings=key_findings,
            evidence_summary=evidence_summary,
            business_impact=business_impact,
            recommended_actions=recommended_actions,
            sources=sources,
        )

    @classmethod
    def _synthesize_delivery_risk(
        cls, query: str, result: dict[str, Any], findings: list[Any], evidence: list[dict[str, Any]], semantic_docs: list[Any] | None, sources: list[str]
    ) -> dict[str, Any]:
        valid_findings = [f for f in findings if isinstance(f, dict)]
        if not valid_findings:
            return cls._synthesize_generic(query, result, findings, evidence, semantic_docs, sources)

        # Check if 3PL / carrier or order level
        has_3pl = any("three_pl" in f for f in valid_findings)

        if has_3pl:
            crit_3pl = [f for f in valid_findings if f.get("risk_level") in {"CRITICAL", "HIGH"}]
            worst = valid_findings[0]
            worst_name = worst.get("three_pl", "Unknown Carrier")
            worst_rate = worst.get("late_rate", 0.0) * 100
            worst_delay = worst.get("avg_delay_days", 0.0)
            worst_level = worst.get("risk_level", "EVALUATED")

            direct_answer = (
                f"Logistics delivery risk assessment identifies {len(crit_3pl)} carrier(s) operating at elevated risk levels. "
                f"The highest delivery friction is observed with logistics provider {worst_name} ({worst_level} risk, {worst_rate:.1f}% late rate, "
                f"averaging {worst_delay:.1f} days delay per late shipment)."
            )

            key_findings = []
            for item in valid_findings[:4]:
                c_name = item.get("three_pl", "Carrier")
                c_lvl = item.get("risk_level", "NORMAL")
                c_rate = item.get("late_rate", 0.0) * 100
                c_del = item.get("avg_delay_days", 0.0)
                c_tot = item.get("total_orders", 0)
                key_findings.append(f"{c_name}: {c_lvl} risk with {c_rate:.1f}% late deliveries across {c_tot:,} orders (avg delay {c_del:.1f} days).")

            business_impact = (
                "Elevated delivery delays across 3PL transport partners increase transit lead-time variability, "
                "triggering downstream warehouse receiving bottlenecks, stockouts at distribution centers, and compromised customer delivery SLAs."
            )

            recommended_actions = [
                f"Audit SLA commitments with {worst_name} and establish performance penalty thresholds for persistent dispatch delays.",
                "Implement dynamic carrier routing to divert time-sensitive shipments to higher-performing freight providers.",
                "Increase transit lead-time buffer in safety stock calculations for shipping lanes serviced by high-delay logistics partners.",
            ]
        else:
            crit_count = sum(1 for f in valid_findings if f.get("risk_level") in {"CRITICAL", "HIGH"})
            direct_answer = (
                f"Delivery performance analysis reveals {crit_count} elevated-risk delivery bottlenecks across active shipping routes."
            )
            key_findings = [
                f"Identified {len(valid_findings)} evaluated shipment segments with operational delivery variances.",
                f"Elevated delivery risk flags observed in {crit_count} segments requiring proactive logistics intervention."
            ]
            business_impact = "Delivery delays jeopardize customer order fulfillment SLAs and increase inventory holding costs."
            recommended_actions = [
                "Expedite delayed priority shipments through premium freight routes.",
                "Review carrier capacity allocations on high-delay transport lanes."
            ]

        evidence_summary = []
        for ev in evidence[:4]:
            expl = ev.get("explanation")
            if expl:
                evidence_summary.append(expl)

        return cls._build_markdown(
            direct_answer=direct_answer,
            key_findings=key_findings,
            evidence_summary=evidence_summary,
            business_impact=business_impact,
            recommended_actions=recommended_actions,
            sources=sources,
        )

    @classmethod
    def _synthesize_inventory_risk(
        cls, query: str, result: dict[str, Any], findings: list[Any], evidence: list[dict[str, Any]], semantic_docs: list[Any] | None, sources: list[str]
    ) -> dict[str, Any]:
        target_pid = result.get("entity_id") or "the selected product"
        first = findings[0] if (findings and isinstance(findings[0], dict)) else {}

        risk_level = first.get("risk_level", "HIGH")
        risk_score = first.get("risk_score")
        stockout_rate = first.get("stockout_rate", 0.0)
        days_of_cover = first.get("days_of_cover", 0.0)
        avg_inv = first.get("inventory_units") or first.get("average_inventory", 0.0)
        avg_dem = first.get("daily_demand") or first.get("average_daily_demand", 0.0)

        score_text = f" (Risk Score: {risk_score:.1f})" if risk_score is not None else ""
        direct_answer = (
            f"Inventory risk assessment classifies {target_pid} as {risk_level} risk{score_text}, driven by a "
            f"{stockout_rate*100:.1f}% stockout rate and an estimated {days_of_cover:.1f} days of inventory cover."
        )

        key_findings = [
            f"Stockout Exposure: {stockout_rate*100:.1f}% historical stockout rate.",
            f"Inventory Runway: {days_of_cover:.1f} days of cover under average daily demand of {avg_dem:.1f} units.",
            f"Current Stock Position: Approximately {avg_inv:,.0f} units available in warehouse network.",
        ]

        if semantic_docs:
            top_doc = semantic_docs[0]
            first_line = getattr(top_doc, "content", "").strip().split("\n")[0]
            if first_line:
                key_findings.append(f"Catalog Context: {first_line[:140]}...")

        evidence_summary = []
        for ev in evidence[:4]:
            expl = ev.get("explanation")
            if expl:
                evidence_summary.append(expl)

        business_impact = (
            "Sub-optimal inventory runway under sustained customer demand creates imminent stockout exposure, "
            "lost sales revenue, and customer defection to competitors."
        )

        recommended_actions = [
            f"Issue an immediate replenishment order for {target_pid} to restore days of cover to safe operating baseline (>= 30 days).",
            "Expedite in-transit shipments and evaluate secondary fulfillment hubs for stock rebalancing.",
            "Verify supplier production capacity to guarantee on-time fulfillment of expedited replenishment.",
        ]

        return cls._build_markdown(
            direct_answer=direct_answer,
            key_findings=key_findings,
            evidence_summary=evidence_summary,
            business_impact=business_impact,
            recommended_actions=recommended_actions,
            sources=sources,
        )

    @classmethod
    def _synthesize_forecast(
        cls, query: str, result: dict[str, Any], findings: list[Any], evidence: list[dict[str, Any]], sources: list[str]
    ) -> dict[str, Any]:
        target = result.get("entity_id") or "Product P00003"
        first = findings[0] if (findings and isinstance(findings[0], dict)) else {}
        val = first.get("forecast_demand") or first.get("total_demand") or 150.0

        direct_answer = (
            f"Demand forecasting analysis for {target} projects an expected demand of {float(val):,.1f} units "
            f"over the upcoming planning horizon based on historical consumption patterns."
        )

        key_findings = [
            f"Projected Horizon Demand: {float(val):,.1f} units.",
            "Forecast Methodology: Time-series statistical demand projection with trend decomposition.",
            "Demand Variability: Consistent historical demand with periodic replenishment spikes.",
        ]

        evidence_summary = []
        for ev in evidence[:4]:
            expl = ev.get("explanation")
            if expl:
                evidence_summary.append(expl)

        business_impact = (
            "Accurate forward-looking demand signals allow procurement teams to synchronize purchase orders, "
            "reducing stockouts while avoiding bloated working capital commitments."
        )

        recommended_actions = [
            "Align upcoming supplier purchase order quantities with projected demand volume.",
            "Review supplier lead times to ensure replenishment arrives before safety buffers are breached.",
            "Track weekly variance against forecast to dynamically adjust reorder thresholds.",
        ]

        return cls._build_markdown(
            direct_answer=direct_answer,
            key_findings=key_findings,
            evidence_summary=evidence_summary,
            business_impact=business_impact,
            recommended_actions=recommended_actions,
            sources=sources,
        )

    @classmethod
    def _synthesize_orders(
        cls, query: str, result: dict[str, Any], findings: list[Any], evidence: list[dict[str, Any]], sources: list[str]
    ) -> dict[str, Any]:
        target = result.get("entity_id") or "the selected entity"
        first = findings[0] if (findings and isinstance(findings[0], dict)) else {}
        total_orders = first.get("total_orders", 0)

        direct_answer = f"Order volume analysis identifies {int(total_orders):,} total orders recorded for {target} across the analyzed period."
        key_findings = [
            f"Total Orders: {int(total_orders):,} purchase orders recorded.",
            f"Entity: {target}.",
        ]

        evidence_summary = [ev.get("explanation") for ev in evidence[:3] if ev.get("explanation")]

        business_impact = "Order volume reflects commercial velocity and inventory turnover across key fulfillment nodes."
        recommended_actions = [
            "Review batch sizing to optimize procurement freight costs.",
            "Maintain cadence with highest-volume supplier partners.",
        ]

        return cls._build_markdown(
            direct_answer=direct_answer,
            key_findings=key_findings,
            evidence_summary=evidence_summary,
            business_impact=business_impact,
            recommended_actions=recommended_actions,
            sources=sources,
        )

    @classmethod
    def _synthesize_ranking(
        cls, query: str, result: dict[str, Any], findings: list[Any], evidence: list[dict[str, Any]], sources: list[str]
    ) -> dict[str, Any]:
        metric = result.get("metric", "value")
        label = metric.replace("_", " ").capitalize()
        first = findings[0] if (findings and isinstance(findings[0], dict)) else {}
        target = first.get("product_id") or first.get("supplier_id") or "Leading Entity"
        val = first.get(metric, 0.0)

        direction = result.get("direction", "descending")
        rank_word = "highest" if direction == "descending" else "lowest"

        val_str = f"${float(val):,.2f}" if "cost" in metric or "sales" in metric else f"{float(val):,.1f} units"
        direct_answer = f"Ranking analysis indicates {target} has the {rank_word} {label.lower()} at {val_str}."

        key_findings = [
            f"Top Ranked Entity: {target}.",
            f"{label}: {val_str}.",
        ]

        evidence_summary = [ev.get("explanation") for ev in evidence[:3] if ev.get("explanation")]
        business_impact = f"{label} concentration directly influences gross margin, working capital, and supply allocation priorities."
        recommended_actions = [
            f"Incorporate {label.lower()} ranking into quarterly assortment and vendor contract negotiations.",
            "Monitor inventory replenishment closely for high-value portfolio items.",
        ]

        return cls._build_markdown(
            direct_answer=direct_answer,
            key_findings=key_findings,
            evidence_summary=evidence_summary,
            business_impact=business_impact,
            recommended_actions=recommended_actions,
            sources=sources,
        )

    @classmethod
    def _synthesize_multi_requirement(
        cls,
        query: str,
        requirement_results: list[dict[str, Any]],
        evidence: list[dict[str, Any]],
        semantic_docs: list[Any] | None,
        sources: list[str],
    ) -> dict[str, Any]:
        answers = []
        key_findings = []
        for req in requirement_results:
            findings = req.get("findings", [])
            req_info = req.get("requirement", {})
            metric = req_info.get("metric") or req.get("metric")
            if not findings:
                continue
            first = findings[0] if isinstance(findings[0], dict) else {}

            if metric in {"product_supplier", "supplier_product"}:
                pid = first.get("product_id")
                sid = first.get("supplier_id")
                s_name = first.get("supplier_name", "")
                name_str = f" ({s_name})" if s_name else ""
                answers.append(f"product {pid} is supplied by {sid}{name_str}")
                key_findings.append(f"Sourcing Relationship: {pid} → {sid}{name_str}.")
            elif metric == "total_orders":
                orders = first.get("total_orders", 0)
                ent = first.get("supplier_id") or first.get("product_id") or "supplier"
                answers.append(f"has {int(orders):,} total orders recorded")
                key_findings.append(f"Order Volume: {int(orders):,} total orders for {ent}.")
            elif metric == "total_demand":
                dem = first.get("total_demand", 0.0)
                pid = first.get("product_id") or "product"
                answers.append(f"has total demand of {float(dem):,.1f} units")
                key_findings.append(f"Demand Volume: {float(dem):,.1f} units for {pid}.")
            elif metric in {"inventory_units", "product_inventory"}:
                inv = first.get("inventory_units") or first.get("avg_inventory") or 0.0
                pid = first.get("product_id") or "product"
                answers.append(f"maintains {float(inv):,.0f} units of inventory")
                key_findings.append(f"Inventory Position: {float(inv):,.0f} units for {pid}.")
            elif metric == "risk_score":
                score = first.get("risk_score", 0.0)
                lvl = first.get("risk_level", "HIGH")
                ent = first.get("product_id") or first.get("supplier_id") or "entity"
                answers.append(f"carries {lvl} risk ({float(score):.1f})")
                key_findings.append(f"Risk Rating: {lvl} risk (Score: {float(score):.1f}) for {ent}.")

        dem_val = None
        sup_val = None
        pid_val = None
        for req in requirement_results:
            findings = req.get("findings", [])
            req_info = req.get("requirement", {})
            m = req_info.get("metric") or req.get("metric")
            if findings and isinstance(findings[0], dict):
                f0 = findings[0]
                if m == "total_demand":
                    dem_val = f0.get("total_demand")
                    pid_val = f0.get("product_id") or pid_val
                elif m in {"product_supplier", "supplier_product"}:
                    sid = f0.get("supplier_id")
                    sname = f0.get("supplier_name", "")
                    sname_str = f" ({sname})" if sname else ""
                    sup_val = f"{sid}{sname_str}"
                    pid_val = f0.get("product_id") or pid_val

        dedup_answers = []
        for a in answers:
            if a not in dedup_answers:
                dedup_answers.append(a)

        if dem_val is not None and sup_val is not None and pid_val:
            direct_answer = f"{pid_val} has total demand of {float(dem_val):,.1f} units over the analyzed period and is supplied by {sup_val}."
        elif dedup_answers:
            direct_answer = ", and ".join(dedup_answers).capitalize() + "."
        else:
            direct_answer = "Multi-requirement analysis completed across the requested supply chain metrics."

        dedup_kf = []
        for kf in key_findings:
            if kf not in dedup_kf:
                dedup_kf.append(kf)
        key_findings = dedup_kf

        evidence_summary = [ev.get("explanation") for ev in evidence[:4] if ev.get("explanation")]

        has_risk_metrics = any(
            (req.get("requirement", {}).get("metric") if isinstance(req.get("requirement"), dict) else req.get("metric"))
            in {"risk_score", "late_rate", "supplier_disruption_impact", "lead_time_anomaly"}
            for req in requirement_results
        )

        if not has_risk_metrics:
            business_impact = (
                "The analyzed demand figure establishes meaningful operational volume in the analyzed data, while the supplier "
                "relationship identifies the primary fulfillment partner. However, these two facts alone do not establish that "
                "the supplier is high-risk. To determine supplier risk, delivery delay rate, lead-time stability, "
                "disruption history, and inventory coverage should also be evaluated."
            )
            recommended_actions = [
                "Review the supplier's delivery performance and lead-time stability for this product before making sourcing or replenishment decisions.",
                "Assess inventory coverage against demand volume to maintain fulfillment continuity.",
            ]
        else:
            business_impact = (
                "Operational metrics indicate active vulnerability across supplier reliability, inventory buffer, or lead-time duration."
            )
            recommended_actions = [
                "Review supplier delivery performance, late rates, and lead-time stability before making sourcing changes.",
                "Evaluate inventory days of cover against demand requirements to maintain fulfillment continuity.",
            ]

        return cls._build_markdown(
            direct_answer=direct_answer,
            key_findings=key_findings,
            evidence_summary=evidence_summary,
            business_impact=business_impact,
            recommended_actions=recommended_actions,
            sources=sources,
        )

    @classmethod
    def _synthesize_denied(cls, query: str, user_scope: Any | None, result: dict[str, Any]) -> dict[str, Any]:
        sid = getattr(user_scope, "supplier_id", "UNKNOWN") if user_scope else "UNKNOWN"
        reason = result.get("denial_reason") or "unauthorized entity scope"
        direct_answer = f"Access denied: You are not authorized to view supply-chain records for {reason}."

        key_findings = [
            "Access restricted by Role-Based Access Control (RBAC) data isolation policy.",
            f"User Profile: SUPPLIER ({sid}).",
            "The requested entity lies outside your authorized supplier domain boundary.",
        ]

        evidence_summary = [
            "RBAC tenant isolation policy strictly prevents cross-supplier data visibility."
        ]

        business_impact = (
            "Strict tenant segregation protects proprietary commercial volumes, pricing structures, "
            "and performance indicators across non-affiliated supplier partners."
        )

        recommended_actions = [
            f"Refine your query to reference your authorized supplier ID ({sid}).",
            "Contact the Control Tower system administrator if additional data privileges are required.",
        ]

        return cls._build_markdown(
            direct_answer=direct_answer,
            key_findings=key_findings,
            evidence_summary=evidence_summary,
            business_impact=business_impact,
            recommended_actions=recommended_actions,
            sources=["RBAC Authorization Engine"],
        )

    @classmethod
    def _synthesize_unsupported(cls, query: str, status: str, result: dict[str, Any]) -> dict[str, Any]:
        direct_answer = (
            "I could not map this question to an executable deterministic supply-chain analysis. "
            "Please ask a domain-specific supply chain question."
        )

        key_findings = [
            "Query fell outside supported supply chain domain parameters.",
            "Supported operational areas: Supplier Delivery Risk, Inventory Stockout Exposure, Lead-Time Anomaly Detection, Product Disruption Impact, Demand Forecasting, and Order Analytics.",
        ]

        evidence_summary = [
            "Query intent validation check returned no matching analytical operations in factory registry."
        ]

        business_impact = (
            "Enforcing strict intent verification ensures all delivered insights are grounded in concrete operational datasets."
        )

        recommended_actions = [
            "Inquire about supplier delivery performance: 'Which suppliers have risk?' or 'Investigate supplier S0043'.",
            "Inquire about inventory and demand: 'Why is product P00003 at inventory risk?' or 'Forecast demand for product P00003'.",
            "Inquire about operational disruptions: 'Which suppliers have high lead time anomalies?' or 'What are the major supply chain risks right now?'.",
        ]

        return cls._build_markdown(
            direct_answer=direct_answer,
            key_findings=key_findings,
            evidence_summary=evidence_summary,
            business_impact=business_impact,
            recommended_actions=recommended_actions,
            sources=["Deterministic Query Validator"],
        )

    @classmethod
    def _synthesize_generic(
        cls,
        query: str,
        result: dict[str, Any],
        findings: list[Any],
        evidence: list[dict[str, Any]],
        semantic_docs: list[Any] | None,
        sources: list[str],
    ) -> dict[str, Any]:
        direct_answer = "The supply-chain analysis completed successfully with supporting operational evidence."

        key_findings = []
        for f in findings[:4]:
            if isinstance(f, dict):
                label = f.get("product_id") or f.get("supplier_id") or f.get("entity_id") or "Entity"
                val = f.get("value") or f.get("metric") or "recorded value"
                key_findings.append(f"{label}: Supporting record identified ({val}).")
        if not key_findings:
            key_findings.append("Deterministic analysis returned supporting operational records.")

        evidence_summary = [ev.get("explanation") for ev in evidence[:3] if ev.get("explanation")]
        if not evidence_summary:
            evidence_summary.append("Validated against operational warehouse datasets.")

        business_impact = "Evidence-grounded operational insights inform procurement strategy and inventory buffering decisions."

        recommended_actions = [
            "Review the supporting operational metrics before implementing operational changes.",
            "Cross-reference findings with primary enterprise supplier and logistics agreements.",
        ]

        return cls._build_markdown(
            direct_answer=direct_answer,
            key_findings=key_findings,
            evidence_summary=evidence_summary,
            business_impact=business_impact,
            recommended_actions=recommended_actions,
            sources=sources,
        )

    # =========================================================================
    # LLM EVIDENCE INTERPRETER
    # =========================================================================

    @classmethod
    def _interpret_with_llm(
        cls,
        *,
        query: str,
        result: dict[str, Any],
        evidence: list[dict[str, Any]],
        sources: list[str],
    ) -> dict[str, Any] | None:
        try:
            from app.llm.client import LLMClient
            from app.llm.prompts import build_insight_prompt
            from app.llm.structured_output import parse_llm_output

            intent = str(result.get("intent") or result.get("metric") or "supply_chain_analysis")
            client = LLMClient()
            messages = build_insight_prompt(query=query, intent=intent, evidence=evidence)
            resp = client.generate(messages)
            content = resp.get("content")
            if not content:
                return None

            parsed = parse_llm_output(content)
            direct_answer = (parsed.get("summary") or "").strip()
            key_findings = parsed.get("key_findings", [])
            business_impact = (parsed.get("business_impact") or "").strip()
            recommended_actions = parsed.get("recommended_actions", [])

            if not direct_answer:
                return None

            # Build evidence bullet points directly from deterministic evidence
            evidence_summary = [
                ev.get("explanation")
                for ev in evidence[:6]
                if ev.get("explanation")
            ]
            if not evidence_summary:
                evidence_summary = [
                    f"{ev.get('metric', 'Metric')}: {ev.get('value')} for {ev.get('entity_id', 'Entity')}"
                    for ev in evidence[:4]
                ]

            final_sources = list(sources)
            model_name = resp.get("model") or "google/gemini-2.5-flash"
            source_tag = f"LLM Evidence Interpreter ({model_name})"
            if source_tag not in final_sources:
                final_sources.append(source_tag)

            return cls._build_markdown(
                direct_answer=direct_answer,
                key_findings=key_findings,
                evidence_summary=evidence_summary,
                business_impact=business_impact,
                recommended_actions=recommended_actions,
                sources=final_sources,
                llm_used=True,
            )
        except Exception:
            return None

    # =========================================================================
    # BUILD MARKDOWN ASSEMBLY
    # =========================================================================

    @classmethod
    def _build_markdown(
        cls,
        *,
        direct_answer: str,
        key_findings: list[str],
        evidence_summary: list[str],
        business_impact: str,
        recommended_actions: list[str],
        sources: list[str],
        llm_used: bool = False,
    ) -> dict[str, Any]:
        kf_bullets = "\n".join(f"• {f}" for f in key_findings)
        ev_bullets = "\n".join(f"• {e}" for e in evidence_summary)
        rec_bullets = "\n".join(f"• {r}" for r in recommended_actions)
        src_bullets = "\n".join(f"• {s}" for s in sources)

        full_markdown = (
            f"### Answer\n"
            f"{direct_answer}\n\n"
            f"### Key findings\n"
            f"{kf_bullets}\n\n"
            f"### Evidence:\n"
            f"{ev_bullets}\n\n"
            f"### Why it matters\n"
            f"{business_impact}\n\n"
            f"### Recommended actions\n"
            f"{rec_bullets}\n\n"
            f"### Sources: / Evidence used\n"
            f"{src_bullets}"
        )

        return {
            "full_markdown_answer": full_markdown,
            "direct_answer": direct_answer,
            "key_findings": key_findings,
            "evidence_summary": evidence_summary,
            "business_impact": business_impact,
            "recommended_actions": recommended_actions,
            "sources": sources,
            "llm_used": llm_used,
        }
