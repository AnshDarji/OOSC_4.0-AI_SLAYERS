from app.knowledge.bm25_manager import bm25_manager
import logging

logging.basicConfig(level=logging.INFO)
print("Rebuilding BM25 index...")
bm25_manager.rebuild_index("global")
print("BM25 Rebuilt!")
