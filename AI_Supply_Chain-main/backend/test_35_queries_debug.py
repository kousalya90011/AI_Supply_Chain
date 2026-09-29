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

def main():
    service = QueryService()
    for qid, qtext, scope in TEST_35:
        try:
            res = service.query(qtext, user_scope=scope)
            status = res.get("status")
            intent = res.get("intent")
            op = res.get("operation")
            metric = res.get("metric")
            cond = res.get("condition")
            dir_ = res.get("direction")
            ev = res.get("evidence", [])
            s_ev = [e for e in ev if isinstance(e, dict) and e.get("retrieval_method") == "structured"]
            m_ev = [e for e in ev if isinstance(e, dict) and e.get("retrieval_method") == "semantic"]
            ans = (res.get("answer") or "")[:120].replace("\n", " ")
            print(f"[{qid:02d}] {qtext}")
            print(f"     Status: {status} | Intent: {intent} | Op: {op} | Metric: {metric} | Cond: {cond} | Dir: {dir_} | Ev: {len(s_ev)}s/{len(m_ev)}m")
            print(f"     Ans: {ans[:90]}...")
        except Exception as e:
            print(f"[{qid:02d}] {qtext} -> ERROR: {e}")

if __name__ == "__main__":
    main()
