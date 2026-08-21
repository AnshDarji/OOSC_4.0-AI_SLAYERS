import os, sys
sys.path.append(os.getcwd())
from app.knowledge.embeddings import embedding_service
from app.knowledge.hybrid_retriever import hybrid_retriever

query = "I filed an RTI 60 days ago to know my property mutation status but got no reply."
emb = embedding_service.embed_texts([query])[0]
chunks = hybrid_retriever.search(query=query, query_embedding=emb, n_results=12, where={"tenant_id": "global"})

print("RETRIEVED CHUNKS:")
for i, c in enumerate(chunks):
    print(f"[{i+1}] {c['metadata'].get('source_name')} | Score: {c['score']:.4f}")
    print(c['text'][:100].replace('\n', ' '))
    print("-")
