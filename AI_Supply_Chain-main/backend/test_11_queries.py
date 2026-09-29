import sys
import json
import logging
from pathlib import Path

# Setup paths
backend_dir = Path(r"c:\Users\CHILUKURI KOUSALYA\Downloads\AI_Supply_Chain-main\AI_Supply_Chain-main\backend")
sys.path.insert(0, str(backend_dir))

from app.services.query_service import QueryService
from app.models.entities import UserRole
from app.query.scope import QueryScope

logging.basicConfig(level=logging.ERROR)

TEST_QUERIES = [
    {
        "id": 1,
        "query": "Which products are affected by supplier disruptions?",
        "scope": QueryScope(username="admin", role=UserRole.ADMIN.value)
    },
    {
        "id": 2,
        "query": "Which products are NOT affected by supplier disruptions?",
        "scope": QueryScope(username="admin", role=UserRole.ADMIN.value)
    },
    {
        "id": 3,
        "query": "Which suppliers have high delivery risk?",
        "scope": QueryScope(username="admin", role=UserRole.ADMIN.value)
    },
    {
        "id": 4,
        "query": "Which suppliers have low delivery risk?",
        "scope": QueryScope(username="admin", role=UserRole.ADMIN.value)
    },
    {
        "id": 5,
        "query": "Which suppliers have the highest delivery risk?",
        "scope": QueryScope(username="admin", role=UserRole.ADMIN.value)
    },
    {
        "id": 6,
        "query": "Identify unusual changes in supplier lead times.",
        "scope": QueryScope(username="admin", role=UserRole.ADMIN.value)
    },
    {
        "id": 7,
        "query": "Why is product P00003 at inventory risk?",
        "scope": QueryScope(username="admin", role=UserRole.ADMIN.value)
    },
    {
        "id": 8,
        "query": "What is the demand for product P00003 and which supplier is associated with it?",
        "scope": QueryScope(username="admin", role=UserRole.ADMIN.value)
    },
    {
        "id": 9,
        "query": "Who supplied product P00003 and how many total orders from this supplier?",
        "scope": QueryScope(username="admin", role=UserRole.ADMIN.value)
    },
    {
        "id": 10,
        "query": "What is my performance in delivery?",
        "scope": QueryScope(username="supplier_user1", role=UserRole.SUPPLIER.value, supplier_id="S0147", scope_type="SUPPLIER_ONLY")
    },
    {
        "id": 11,
        "query": "What is the weather forecast for Tokyo tomorrow?",
        "scope": QueryScope(username="admin", role=UserRole.ADMIN.value)
    }
]

def run_tests():
    service = QueryService()
    results = []

    print("=" * 80)
    print("RUNNING 11 TEST QUERIES")
    print("=" * 80)

    for item in TEST_QUERIES:
        q_id = item["id"]
        q_text = item["query"]
        scope = item["scope"]

        print(f"\n--- Running Test #{q_id}: '{q_text}' (Scope: role={scope.role}, supplier_id={scope.supplier_id}) ---")
        try:
            res = service.query(q_text, user_scope=scope)

            # Extract fields
            intent = res.get("intent")
            operation = res.get("operation")
            condition = res.get("condition")
            query_plan = res.get("query_plan")
            fallback_used = res.get("fallback_used")
            retrieval_method = res.get("retrieval_method")
            execution_status = res.get("status")
            all_evidence = res.get("evidence", [])
            structured_evidence = [e for e in all_evidence if isinstance(e, dict) and e.get("retrieval_method") == "structured"]
            semantic_evidence = [e for e in all_evidence if isinstance(e, dict) and e.get("retrieval_method") == "semantic"]
            final_evidence = all_evidence
            llm_answer = res.get("answer") or res.get("response") or res.get("message") or ""

            print(f"Status: {execution_status} | Fallback Used: {fallback_used} | Intent: {intent}")
            print(f"Operation: {operation} | Condition: {condition} | Retrieval: {retrieval_method}")
            print(f"Structured Evidence Count: {len(structured_evidence)}")
            print(f"Semantic Evidence Count: {len(semantic_evidence)}")
            preview = llm_answer[:300].encode('ascii', 'backslashreplace').decode('ascii')
            print(f"LLM Answer Preview:\n{preview}...")

            results.append({
                "id": q_id,
                "query": q_text,
                "intent": intent,
                "operation": operation,
                "condition": condition,
                "query_plan": query_plan,
                "execution_status": execution_status,
                "fallback_used": fallback_used,
                "retrieval_method": retrieval_method,
                "structured_evidence_sample": structured_evidence[:2] if structured_evidence else [],
                "semantic_evidence_sample": semantic_evidence[:1] if semantic_evidence else [],
                "llm_answer": llm_answer
            })
        except Exception as e:
            print(f"ERROR in Test #{q_id}: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "id": q_id,
                "query": q_text,
                "error": str(e)
            })

    output_path = backend_dir / "test_11_queries_result.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nSaved test results to {output_path}")

if __name__ == "__main__":
    run_tests()
