import json
import sys
from app.services.query_service import QueryService

def main():
    service = QueryService()

    queries = [
        "What are the major supply chain risks?",
        "What are the non major supply chain risks?",
        "Which suppliers have high risk?",
        "Which suppliers have no risk of delivery delays?",
        "Which products are affected by supplier disruptions?",
        "Which products are not affected by supplier disruptions?",
        "Which suppliers have the most delivery delays?",
        "Which suppliers have the least delivery delays?",
        "Which suppliers are not high risk?",
        "Which products have low inventory risk?",
        "Which products do not have stockout exposure?",
        "What are the risks above 60?",
        "What are the risks below 30?",
        "Which suppliers are improving?",
        "Which suppliers are getting worse?",
        "What is my delivery performance?",
        # Target query with evidence explicit
        "What are the non major supply chain risks and what evidence supports them?"
    ]

    print("=" * 80)
    print("RUNNING 16 SEMANTIC REGRESSION TESTS + TARGET QUERY")
    print("=" * 80)

    all_passed = True

    for i, q in enumerate(queries, 1):
        print(f"\n--- [TEST {i}] Query: '{q}' ---")
        try:
            res = service.query(q)
            plan = res.get("query_plan", {})
            findings = res.get("findings", [])
            evidence = res.get("evidence", [])
            exec_status = res.get("execution_status")
            query_answer_status = res.get("query_answer_status")
            status = res.get("status")

            print(f"Domain: {plan.get('domain')} | Metric: {plan.get('metric')} | Op: {plan.get('operation')} | Dir: {plan.get('direction')}")
            print(f"Condition: {plan.get('condition')} | Negative: {plan.get('negative_condition')} | Requires Ev: {plan.get('requires_evidence')}")
            print(f"Status: {status} | Execution Status: {exec_status} | Query Answer Status: {query_answer_status}")
            print(f"Findings Count: {len(findings)} | Evidence Records: {len(evidence)}")

            if findings:
                sample_findings = findings[:2]
                print(f"Sample findings: {sample_findings}")

            # Specific assertion for non-major queries (Requirement 10)
            if "non major" in q.lower():
                # Check that findings and evidence do NOT contain CRITICAL or HIGH risk levels
                for f in findings:
                    rl = str(f.get("risk_level", "")).upper()
                    if rl in {"CRITICAL", "HIGH"}:
                        print(f"FAILURE: non-major query returned major risk level: {rl}")
                        all_passed = False
                for ev in evidence:
                    data = ev.get("data", {})
                    rl = str(data.get("risk_level", "")).upper()
                    if rl in {"CRITICAL", "HIGH"}:
                        print(f"FAILURE: non-major evidence returned major risk level: {rl}")
                        all_passed = False

            # Specific assertion for not high risk
            if "not high risk" in q.lower():
                for f in findings:
                    rl = str(f.get("risk_level", "")).upper()
                    if rl in {"CRITICAL", "HIGH"}:
                        print(f"FAILURE: 'not high risk' returned {rl}")
                        all_passed = False

            # Specific assertion for evidence count > 0 when requires_evidence=True
            if plan.get("requires_evidence") and len(evidence) == 0:
                print(f"FAILURE: Evidence required but 0 evidence records returned!")
                all_passed = False

            # Success condition
            if query_answer_status not in {"PASS", "success"}:
                print(f"WARNING: query_answer_status is {query_answer_status}")
                if exec_status == "success" and len(evidence) == 0:
                    all_passed = False

        except Exception as e:
            print(f"ERROR executing '{q}': {e}")
            import traceback
            traceback.print_exc()
            all_passed = False

    print("\n" + "=" * 80)
    if all_passed:
        print("ALL TESTS PASSED SUCCESSFULLY!")
    else:
        print("SOME TESTS FAILED - SEE LOG ABOVE")
    print("=" * 80)

if __name__ == "__main__":
    main()
