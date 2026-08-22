import json
import sys
import os

# Ensure the root of BACKEND is in the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.knowledge.hybrid_retriever import hybrid_retriever
from app.knowledge.embeddings import embedding_service
from app.ai.domain_classifier import domain_classifier

query = "A municipal authority has repeatedly failed to collect garbage from my residential area for several weeks, resulting in accumulated waste, foul smell, and serious sanitation problems. Despite multiple complaints through the municipal helpline and written complaints to the local ward office, no effective action has been taken. I have photographs and videos of the accumulated garbage, copies of my complaints, complaint numbers, dates, and communications with municipal officials. What legal and administrative remedies are available to me? Give me a step-by-step action plan, identify the exact municipal authorities I should approach and the escalation hierarchy, list all evidence I should preserve, explain whether I can seek directions from a court or other authority if the municipality remains inactive, and identify the relevant statutory provisions and judicial precedents supporting my rights."

predicted_domains = domain_classifier.predict_domain(query)
print("Predicted Domains:", predicted_domains)

query_embedding = embedding_service.embed_query(query)
chunks = hybrid_retriever.search(
    query=query, 
    query_embedding=query_embedding, 
    n_results=12, 
    where=None,
    predicted_domains=predicted_domains.get("domains", {}),
    document_type_priority=predicted_domains.get("document_type_priority", "any")
)

print(f"\nTotal retrieved chunks before filtering: {len(chunks)}")
for i, chunk in enumerate(chunks):
    meta = chunk["metadata"]
    print(f"[{i}] {meta.get('act_name')} | {meta.get('section')} | Type: {meta.get('document_type')} | Method: {meta.get('retrieval_method')} | Rank: {meta.get('retrieval_rank')} | RRF: {meta.get('rrf_score')}")
