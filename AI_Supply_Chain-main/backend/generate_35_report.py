import sys
import json
import logging
from pathlib import Path

backend_dir = Path(r"c:\Users\CHILUKURI KOUSALYA\Downloads\AI_Supply_Chain-main\AI_Supply_Chain-main\backend")
sys.path.insert(0, str(backend_dir))

from app.services.query_service import QueryService
from app.models.entities import UserRole
from app.query.scope import QueryScope

logging.basicConfig(level=logging.ERROR)

TEST_35 = [
    # DELIVERY
    (1, "Which suppliers have risk?", QueryScope(username="admin", role=UserRole.ADMIN.value)),
    (2, "Which suppliers have no risk of delivery delays?", QueryScope(username="admin", role=UserRole.ADMIN.value)),
    (3, "Which suppliers have low delivery risk?", QueryScope(username="admin", role=UserRole.ADMIN.value)),
    (4, "Which suppliers have high delivery risk?", QueryScope(username="admin", role=UserRole.ADMIN.value)),
    (5, "Which suppliers have the highest delivery risk?", QueryScope(username="admin", role=UserRole.ADMIN.value)),
    (6, "Which suppliers have the lowest delivery risk?", QueryScope(username="admin", role=UserRole.ADMIN.value)),
    (7, "Which suppliers have good delivery performance?", QueryScope(username="admin", role=UserRole.ADMIN.value)),
    (8, "Which suppliers are experiencing delivery delays?", QueryScope(username="admin", role=UserRole.ADMIN.value)),
    (9, "What is my performance in delivery?", QueryScope(username="supplier_user1", role=UserRole.SUPPLIER.value, supplier_id="S0147", scope_type="SUPPLIER_ONLY")),
    (10, "How many deliveries were late?", QueryScope(username="supplier_user1", role=UserRole.SUPPLIER.value, supplier_id="S0147", scope_type="SUPPLIER_ONLY")),

    # DISRUPTION
    (11, "Which products are affected by supplier disruptions?", QueryScope(username="admin", role=UserRole.ADMIN.value)),
    (12, "Which products are NOT affected by supplier disruptions?", QueryScope(username="admin", role=UserRole.ADMIN.value)),
    (13, "Which products are most affected by supplier disruptions?", QueryScope(username="admin", role=UserRole.ADMIN.value)),
    (14, "Which products are least affected by supplier disruptions?", QueryScope(username="admin", role=UserRole.ADMIN.value)),
    (15, "Which suppliers are affected by disruptions?", QueryScope(username="admin", role=UserRole.ADMIN.value)),
    (16, "Which suppliers are not affected by disruptions?", QueryScope(username="admin", role=UserRole.ADMIN.value)),

    # INVENTORY
    (17, "Why is P00003 at inventory risk?", QueryScope(username="admin", role=UserRole.ADMIN.value)),
    (18, "Which products have high stockout risk?", QueryScope(username="admin", role=UserRole.ADMIN.value)),
    (19, "Which products have low stockout risk?", QueryScope(username="admin", role=UserRole.ADMIN.value)),
    (20, "Which products have stockout rate above 80%?", QueryScope(username="admin", role=UserRole.ADMIN.value)),
    (21, "Which products have more than 10 days of inventory cover?", QueryScope(username="admin", role=UserRole.ADMIN.value)),

    # LEAD TIME
    (22, "Which suppliers have increasing lead times?", QueryScope(username="admin", role=UserRole.ADMIN.value)),
    (23, "Which suppliers have decreasing lead times?", QueryScope(username="admin", role=UserRole.ADMIN.value)),
    (24, "Which suppliers have unusual lead-time changes?", QueryScope(username="admin", role=UserRole.ADMIN.value)),
    (25, "Which supplier has the largest lead-time increase?", QueryScope(username="admin", role=UserRole.ADMIN.value)),

    # RELATIONSHIPS
    (26, "Who supplies P00003?", QueryScope(username="admin", role=UserRole.ADMIN.value)),
    (27, "Which products does S0147 supply?", QueryScope(username="admin", role=UserRole.ADMIN.value)),
    (28, "What is the demand for P00003 and which supplier provides it?", QueryScope(username="admin", role=UserRole.ADMIN.value)),
    (29, "Which supplier provides the highest-demand products?", QueryScope(username="admin", role=UserRole.ADMIN.value)),

    # COMPARISON
    (30, "Compare S0147 and S0150 delivery performance.", QueryScope(username="admin", role=UserRole.ADMIN.value)),
    (31, "Which supplier has a higher late rate, S0147 or S0150?", QueryScope(username="admin", role=UserRole.ADMIN.value)),

    # FORECAST
    (32, "Forecast demand for P00003.", QueryScope(username="admin", role=UserRole.ADMIN.value)),
    (33, "Is P00003 demand increasing or decreasing?", QueryScope(username="admin", role=UserRole.ADMIN.value)),

    # UNSUPPORTED
    (34, "What is the weather forecast for Tokyo tomorrow?", QueryScope(username="admin", role=UserRole.ADMIN.value)),
    (35, "How many strings are there in a guitar?", QueryScope(username="admin", role=UserRole.ADMIN.value)),
]

def build_normalized_meaning(res):
    parts = []
    if res.get("entity"):
        parts.append(f"entity={res['entity']}")
    if res.get("entity_id"):
        parts.append(f"id={res['entity_id']}")
    if res.get("domain"):
        parts.append(f"domain={res['domain']}")
    if res.get("metric"):
        parts.append(f"metric={res['metric']}")
    if res.get("operation"):
        parts.append(f"operation={res['operation']}")
    if res.get("direction") and res["direction"] != "none":
        parts.append(f"direction={res['direction']}")
    if res.get("condition"):
        parts.append(f"condition={res['condition']}")
    if res.get("negative_condition"):
        parts.append(f"negative=True")
    if res.get("threshold"):
        t = res["threshold"]
        parts.append(f"threshold={t.get('operator')}{t.get('value')}{t.get('unit')}")
    if res.get("trend"):
        parts.append(f"trend={res['trend']}")
    if res.get("comparison"):
        c = res["comparison"]
        parts.append(f"compare={c.get('entities')}")
    if res.get("scope"):
        parts.append(f"scope={res['scope']}")
    return ", ".join(parts) if parts else "unsupported/out_of_domain"

def main():
    service = QueryService()
    results = []

    for qid, qtext, scope in TEST_35:
        try:
            res = service.query(qtext, user_scope=scope)
            ev = res.get("evidence", []) or res.get("combined_evidence", [])
            s_ev = [e for e in ev if isinstance(e, dict) and e.get("retrieval_method") == "structured"]
            m_ev = [e for e in ev if isinstance(e, dict) and e.get("retrieval_method") == "semantic"]
            total_ev = len(ev)
            
            raw_status = res.get("status")
            fallback_used = bool(res.get("fallback_used", False))
            
            # Check PASS criteria
            is_unsupported = qid in (34, 35)
            if is_unsupported:
                pass_status = "PASS" if (fallback_used and raw_status in ("clarification_required", "clarification", "unsupported", "fallback")) else "FAIL"
            else:
                pass_status = "PASS" if (raw_status == "success" and total_ev > 0 and not fallback_used) else "FAIL"

            reqs = res.get("requirements", [])
            req_str = f"{len(reqs)} requirements" if reqs else "1 requirement"
            if res.get("requirement_count", 0) > 1:
                req_str = f"{res.get('successful_requirements', len(reqs))}/{res.get('requirement_count', len(reqs))} resolved"

            norm_meaning = build_normalized_meaning(res)

            item = {
                "id": qid,
                "query": qtext,
                "normalized_meaning": norm_meaning,
                "intent": res.get("intent"),
                "entity": res.get("entity_type") or res.get("entity"),
                "operation": res.get("operation"),
                "metric": res.get("metric"),
                "condition": res.get("condition"),
                "direction": res.get("direction"),
                "requirements": req_str,
                "structured_evidence_count": len(s_ev),
                "semantic_evidence_count": len(m_ev),
                "total_evidence_count": total_ev,
                "retrieval_method": res.get("retrieval_mode", "structured"),
                "fallback_used": fallback_used,
                "status": pass_status,
                "raw_status": raw_status,
                "direct_answer": res.get("direct_answer", ""),
                "final_answer": res.get("answer", "")
            }
            results.append(item)
            print(f"[{qid:02d}] {pass_status} | {qtext[:45]:45} | op={res.get('operation')} | cond={res.get('condition')} | ev={len(s_ev)}s/{len(m_ev)}m | {res.get('direct_answer','')[:60]}")
        except Exception as e:
            print(f"[{qid:02d}] ERROR: {qtext} -> {e}")
            results.append({
                "id": qid,
                "query": qtext,
                "status": "FAIL",
                "error": str(e)
            })

    output_path = backend_dir / "test_35_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved full results to {output_path}")

if __name__ == "__main__":
    main()
