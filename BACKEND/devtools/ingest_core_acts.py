import os
import sys
import logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.knowledge.chunking import semantic_chunker
from app.knowledge.embeddings import embedding_service
from app.knowledge.vector_store import vector_store

logging.basicConfig(level=logging.INFO)

files_to_ingest = [
    "RIGHT_TO_INFORMATION_ACT_2005.md",
    "CONSUMER_PROTECTION_ACT_2019.md",
    "MAHARASHTRA_RENT_CONTROL_ACT_1999.md"
]

corpus_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "corpus")

for filename in files_to_ingest:
    filepath = os.path.join(corpus_dir, filename)
    if not os.path.exists(filepath):
        print(f"NOT FOUND: {filepath}")
        continue
        
    print(f"Ingesting {filename}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
        
    base_metadata = {
        "source_name": filename.replace(".md", ""),
        "document_id": filename,
        "type": "statute"
    }
    
    chunks = semantic_chunker.chunk_text(text, base_metadata)
    texts_to_embed = [c["text"] for c in chunks]
    print(f"Embedding {len(chunks)} chunks...")
    embeddings = embedding_service.embed_texts(texts_to_embed)
    
    vector_store.add_chunks(
        ids=[c["id"] for c in chunks],
        embeddings=embeddings,
        documents=texts_to_embed,
        metadatas=[c["metadata"] for c in chunks]
    )
    print(f"Done ingesting {filename}")

print("Rebuilding Global BM25...")
from app.knowledge.bm25_manager import bm25_manager
bm25_manager.rebuild_index("global")
print("Targeted ingestion complete!")
