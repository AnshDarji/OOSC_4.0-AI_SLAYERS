import chromadb
from app.knowledge.vector_store import vector_store

try:
    collection = vector_store.collection
    print("Total dense vectors:", collection.count())
    
    docs = collection.get(limit=100000, include=['metadatas'])
    metadatas = docs.get('metadatas', [])
    domains = set([m.get('legal_domain', 'Unknown') for m in metadatas if m])
    types = set([m.get('type', 'Unknown') for m in metadatas if m])
    sources = set([m.get('source_name', 'Unknown') for m in metadatas if m])
    
    print("Total dense metadata items:", len(metadatas))
    print("Domains found:", domains)
    print("Types found:", types)
    print("Sources found:", len(sources), "unique sources")
except Exception as e:
    print("Error inspecting dense:", e)

from app.knowledge.bm25_manager import bm25_manager
bm25, c_ids, c_docs, c_meta = bm25_manager.get_index("global")
if bm25:
    print("Total sparse documents:", len(c_docs))
    s_types = set([m.get('type', 'Unknown') for m in c_meta])
    s_sources = set([m.get('source_name', 'Unknown') for m in c_meta])
    print("Sparse types:", s_types)
    print("Sparse sources:", len(s_sources), "unique sources")
else:
    print("BM25 index not loaded.")
