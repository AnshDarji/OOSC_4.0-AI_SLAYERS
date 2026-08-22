import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from app.knowledge.vector_store import vector_store

print("SC count:", vector_store.sc_collection.count())
