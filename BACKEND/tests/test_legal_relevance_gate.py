import json
from app.ai.orchestrator import rag_orchestrator

tests = [
    {
        "name": "Garbage Collection (Municipal Sanitation)",
        "query": "Municipal authority fails to collect garbage. What are my remedies?",
        "must_not_contain": ["RIGHT_OF_CHILDREN_TO_FREE_AND_COMPULSORY_EDUCATION_ACT_2009"]
    },
    {
        "name": "Tenant Eviction (Rent Control)",
        "query": "Landlord cuts electricity to force tenant to vacate.",
        "must_not_contain": ["ELECTRICITY_ACT_2003"] # Assuming it retrieves this incorrectly normally just because of 'electricity'
    }
]

print("Running Legal Relevance Gate Regression Suite...")

for t in tests:
    print(f"\\n--- Testing: {t['name']} ---")
    res = rag_orchestrator.trigger_pipeline(t['query'], filters={}, task_type='QA')
    sources = [c.get("source_name", "") for c in res.get("citations", [])]
    print(f"Retrieved Sources: {sources}")
    
    passed = True
    for bad_source in t['must_not_contain']:
        if bad_source in sources:
            print(f"[FAIL] Irrelevant source {bad_source} bypassed the relevance gate!")
            passed = False
    
    if passed:
        print("[PASS] No strictly lexical/irrelevant sources retrieved.")

print("\\nRegression suite complete.")
