import os
import sys
import time

# Add BACKEND to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import settings
from app.ai.orchestrator import rag_orchestrator
from app.knowledge.embeddings import embedding_service
from app.knowledge.bm25_manager import bm25_manager

QUERIES = [
    "My landlord won't return my security deposit",
    "I want to file RTI about road repair funds in my ward",
    "Bought a phone online, arrived broken, seller ignores me",
    "My employer hasn't paid overtime for 3 months",
    "How do I file a consumer complaint online"
]

def run_benchmark():
    print("--- WARMUP ---")
    start = time.time()
    embedding_service.model = None  # Force lazy load behavior
    try:
        bm25_manager.get_index("global")
        # Ensure we use an empty list for history
        rag_orchestrator.trigger_pipeline("Hello", history=[])
    except Exception as e:
        print(f"Warmup failed: {e}")
    print(f"Warmup took: {time.time() - start:.2f}s")
    
    print("\n--- BENCHMARK RUN ---")
    results = []
    
    for i, q in enumerate(QUERIES):
        print(f"\nQuery {i+1}: '{q}'")
        start_q = time.time()
        
        try:
            res = rag_orchestrator.trigger_pipeline(q, history=[])
        except Exception as e:
            print(f"Pipeline crashed: {e}")
            res = {"answer": f"Failed: {e}"}
            
        total_time = time.time() - start_q
        
        metrics = res.get('metrics', {})
        error = False
        if "Failed to generate" in res.get('answer', '') or "Failed:" in res.get('answer', ''):
            error = True
            
        print(f"Time: {total_time:.2f}s | Success: {not error}")
        if not error:
            print(f"  Embedding: {metrics.get('embedding_time', 0)}s")
            print(f"  Retrieval: {metrics.get('retrieval_time', 0)}s")
            print(f"  Generation: {metrics.get('model_processing_time', 0)}s")
            print(f"  Retries/Sleep: {metrics.get('retry_delay_time', 0)}s")
        else:
            print(f"  Answer: {res.get('answer')}")
            
        results.append({
            "query": q,
            "total_time": total_time,
            "success": not error,
            "metrics": metrics
        })
        
    print("\n--- SUMMARY ---")
    successful = [r['total_time'] for r in results if r['success']]
    if successful:
        successful.sort()
        p50 = successful[len(successful)//2]
        p95 = successful[int(len(successful) * 0.95)] if len(successful) > 1 else successful[0]
        print(f"Success Rate: {len(successful)}/{len(QUERIES)}")
        print(f"P50: {p50:.2f}s")
        print(f"P95: {p95:.2f}s")
    else:
        print("All queries failed.")

if __name__ == "__main__":
    run_benchmark()
