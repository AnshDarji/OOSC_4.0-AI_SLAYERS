import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from app.knowledge.vector_store import vector_store
from app.knowledge.embeddings import embedding_service

query = "Supreme Court judgments explaining natural justice, audi alteram partem, and fair hearing before disciplinary dismissal."
query_embedding = embedding_service.embed_query(query)

print("--- Testing Dense Retrieval for SC ---")
sc_results = vector_store.search(query_embedding, n_results=10, where=None, search_sc=True)

for i, res in enumerate(sc_results):
    meta = res["metadata"]
    print(f"[{i}] Distance: {res['distance']:.4f} | Source: {meta.get('source_name')} | File: {meta.get('document_id')}")
    print(f"    Case: {meta.get('case_name', 'N/A')}")
    
print("\n--- Testing BM25 for SC ---")
from app.knowledge.bm25_manager import bm25_manager
import nltk
bm25, corpus_ids, corpus_docs, corpus_metadatas = bm25_manager.get_index("global")
if bm25:
    tokenized_query = nltk.word_tokenize(query.lower())
    scores = bm25.get_scores(tokenized_query)
    sparse_ranking = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    
    sc_count = 0
    for idx in sparse_ranking:
        if sc_count >= 10: break
        meta = corpus_metadatas[idx]
        if meta.get("authority_type") == "judicial" or "SC_" in corpus_ids[idx]:
            print(f"[{sc_count}] Score: {scores[idx]:.4f} | Source: {meta.get('source_name')} | Case: {meta.get('case_name', 'N/A')}")
            sc_count += 1
else:
    print("BM25 index not loaded.")
