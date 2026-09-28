import sys
import os
import pandas as pd
from datetime import datetime

# Test script to verify analytical execution and query synthesizer
sys.path.insert(0, os.path.abspath("backend"))

from app.services.data_service import DataService
from app.services.query_service import QueryService
from app.query.scope import QueryScope

def main():
    ds = DataService()
    res = ds.load_data()
    print("Data loaded successfully:", list(res["datasets"].keys()))
    
    qs = QueryService()
    
    test_queries = [
        "Which suppliers have risk?",
        "Why is product P00003 at inventory risk?",
        "Which suppliers have high lead time anomalies?",
        "Which products have high supplier disruption impact?",
        "What are the major supply chain risks right now?",
        "Investigate supplier S0043",
        "Forecast demand for product P00003",
        "Who supplied product P00003 and how many total orders from this supplier?",
        "What is the capital of France?",
    ]
    
    for q in test_queries:
        print("\n" + "="*60)
        print(f"QUERY: {q}")
        resp = qs.query(q)
        print(f"STATUS: {resp.get('status')} | INTENT: {resp.get('intent')}")
        print("ANSWER:\n" + resp.get("answer", ""))
        print("KEY FINDINGS:", resp.get("key_findings"))
        print("RECOMMENDATIONS:", resp.get("recommendations"))

if __name__ == "__main__":
    main()
