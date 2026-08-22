import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from app.knowledge.vector_store import vector_store

res = vector_store.sc_collection.get(limit=1, include=["metadatas"])
print(res)
