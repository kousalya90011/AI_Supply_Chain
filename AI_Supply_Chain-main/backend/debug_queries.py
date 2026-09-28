import sys
import os

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.abspath("backend"))

from app.services.data_service import DataService
from app.services.query_service import QueryService

ds = DataService()
ds.load_data()
qs = QueryService()

for q in [
    "What is the delivery risk?",
    "What are the major supply chain risks right now?",
    "Who supplied product P00003 and how many total orders from this supplier?",
    "What products are supplied by S0043 and what is their inventory status?",
]:
    print("\n" + "="*70)
    print(f"QUERY: {q}")
    plan = qs.planner.plan(q)
    print("PLAN:", plan.to_dict() if hasattr(plan, "to_dict") else plan)
    res = qs.query(q)
    print(f"STATUS: {res.get('status')} | INTENT: {res.get('intent')}")
    print(res.get("answer"))
