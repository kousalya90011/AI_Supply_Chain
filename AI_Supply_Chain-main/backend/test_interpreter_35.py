import sys
from pathlib import Path
backend_dir = Path(r"c:\Users\CHILUKURI KOUSALYA\Downloads\AI_Supply_Chain-main\AI_Supply_Chain-main\backend")
sys.path.insert(0, str(backend_dir))

from app.query.interpreter import SemanticQueryInterpreter
from test_35_queries_debug import TEST_35

sqi = SemanticQueryInterpreter()

for qid, q, s in TEST_35:
    r = sqi.interpret(q)
    print(f"[{qid:02d}] {q}")
    print(f"     intent={r.get('intent')} | op={r.get('operation')} | metric={r.get('metric')} | dir={r.get('direction')} | cond={r.get('condition')} | trend={r.get('trend')} | thresh={r.get('threshold')} | comp={r.get('comparison')}")
