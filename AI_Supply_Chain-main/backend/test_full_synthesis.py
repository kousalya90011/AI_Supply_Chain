import sys
import os
import time

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.abspath("backend"))

from app.services.data_service import DataService
from app.services.query_service import QueryService
from app.query.scope import QueryScope

def test_queries():
    ds = DataService()
    ds.load_data()
    
    qs = QueryService()
    
    queries = [
        ("Which suppliers have risk?", None),
        ("Why is product P00003 at inventory risk?", None),
        ("What is the delivery risk?", None),
        ("Forecast demand for product P00003", None),
        ("Who supplied product P00003 and how many total orders from this supplier?", None),
        ("What is the demand for product P00003 and which supplier is associated with it?", None),
        ("Which suppliers have high lead time anomalies?", None),
        ("Which products have high supplier disruption impact?", None),
        ("What are the major supply chain risks right now?", None),
        ("Investigate supplier S0043", None),
        ("Supplier delivery risk for S0043", None),
        ("What products are supplied by S0043 and what is their inventory status?", None),
        ("What is the capital of France?", None),
        ("Investigate supplier S0043", QueryScope(username="supplier_user", role="supplier", supplier_id="S0001")),
    ]
    
    print(f"Testing {len(queries)} queries...")
    for idx, (q, scope) in enumerate(queries, 1):
        print(f"\n--- [{idx}] QUERY: {q} (Scope: {scope.supplier_id if scope else 'global'}) ---")
        res = qs.query(q, user_scope=scope)
        print(f"STATUS: {res.get('status')} | INTENT: {res.get('intent')} | RETRIEVAL: {res.get('retrieval_mode')}")
        ans = res.get("answer", "")
        # Check required sections
        sections = ["### Answer", "### Key findings", "### Evidence", "### Why it matters", "### Recommended actions", "### Sources / Evidence used"]
        missing = [s for s in sections if s not in ans]
        if missing:
            print(f"WARNING: Missing sections: {missing}")
        else:
            print("SUCCESS: All 6 sections present.")
        print(ans[:250] + "...")

if __name__ == "__main__":
    test_queries()
