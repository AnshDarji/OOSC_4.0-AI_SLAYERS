import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from app.knowledge.hybrid_retriever import hybrid_retriever
from app.knowledge.embeddings import embedding_service
from app.ai.domain_classifier import domain_classifier

benchmark_queries = {
    "Criminal": "What is the procedure when police refuse to register an FIR?",
    "Constitutional": "Does the right to life under Article 21 include the right to privacy?",
    "Employment": "Employee dismissed without hearing or disclosing allegations. Audi alteram partem in disciplinary proceedings.",
    "Consumer": "I bought a defective product and the seller refuses to refund. What are my rights under Consumer Protection Act?",
    "Property/Tenancy": "Landlord is trying to evict me without notice and cut off essential services like water.",
    "Municipal": "A municipal authority has repeatedly failed to collect garbage from my residential area for several weeks, resulting in accumulated waste, foul smell, and serious sanitation problems.",
    "Administrative": "Public authority failure to perform statutory duty, seeking writ of mandamus.",
    "Supreme Court precedent": "Supreme Court judgments explaining natural justice, audi alteram partem, and fair hearing before disciplinary dismissal."
}

results = {}

print("--- Running Gold Standard Retrieval Benchmark (BASELINE) ---")
for category, query in benchmark_queries.items():
    print(f"\nProcessing category: {category}")
    predicted_domains = domain_classifier.predict_domain(query)
    query_embedding = embedding_service.embed_query(query)
    chunks = hybrid_retriever.search(
        query=query, 
        query_embedding=query_embedding, 
        n_results=10, 
        where=None,
        predicted_domains=predicted_domains.get("domains", {}),
        document_type_priority=predicted_domains.get("document_type_priority", "any")
    )
    
    category_results = []
    for i, chunk in enumerate(chunks):
        meta = chunk["metadata"]
        category_results.append({
            "rank": i+1,
            "source_name": meta.get("source_name", "Unknown"),
            "act_name": meta.get("act_name"),
            "case_name": meta.get("case_name"),
            "type": meta.get("document_type", meta.get("type", "Unknown")),
            "method": meta.get("retrieval_method"),
            "rrf_score": meta.get("rrf_score")
        })
    results[category] = category_results

with open("benchmark_baseline.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=4, ensure_ascii=False)
print("\nBaseline benchmark saved to benchmark_baseline.json")
