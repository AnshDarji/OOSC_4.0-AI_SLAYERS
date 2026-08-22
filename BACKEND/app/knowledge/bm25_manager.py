import os
import pickle
import logging
from typing import List, Dict, Any, Tuple, Optional
import nltk
from rank_bm25 import BM25Okapi
from app.knowledge.vector_store import vector_store

logger = logging.getLogger(__name__)

# Ensure nltk punkt is downloaded
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt', quiet=True)
    nltk.download('punkt_tab', quiet=True)

BM25_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chroma_db", "bm25_cache")

class BM25Manager:
    def __init__(self):
        os.makedirs(BM25_CACHE_DIR, exist_ok=True)
        self._memory_cache = {}

    def _get_cache_path(self, tenant_id: str) -> str:
        safe_tenant = "".join([c if c.isalnum() else "_" for c in tenant_id])
        return os.path.join(BM25_CACHE_DIR, f"bm25_{safe_tenant}.pkl")

    def rebuild_index(self, tenant_id: str = "global"):
        """Fetches all documents for the tenant from ChromaDB and rebuilds the BM25 index."""
        logger.info(f"Rebuilding BM25 index for tenant: {tenant_id}")
        where = {"tenant_id": tenant_id} if tenant_id != "global" else None
        
        corpus_docs = []
        corpus_ids = []
        corpus_metadatas = []
        
        try:
            db_docs = vector_store.collection.get(where=where, include=["documents", "metadatas"])
            corpus_docs.extend(db_docs.get("documents", []))
            corpus_ids.extend(db_docs.get("ids", []))
            corpus_metadatas.extend(db_docs.get("metadatas", []))
            
            # Fetch SC cases if global or matching tenant
            if tenant_id == "global":
                sc_docs = vector_store.sc_collection.get(include=["documents", "metadatas"])
                corpus_docs.extend(sc_docs.get("documents", []))
                corpus_ids.extend(sc_docs.get("ids", []))
                corpus_metadatas.extend(sc_docs.get("metadatas", []))
        except Exception as e:
            logger.error(f"Failed to fetch corpus for BM25 rebuild: {e}")
            return
            
        if not corpus_docs:
            logger.warning(f"No documents found for tenant {tenant_id} to build BM25.")
            return

        tokenized_corpus = [nltk.word_tokenize(doc.lower()) for doc in corpus_docs]
        bm25 = BM25Okapi(tokenized_corpus)
        
        # Save to disk
        cache_path = self._get_cache_path(tenant_id)
        cache_data = {
            "bm25": bm25,
            "corpus_ids": corpus_ids,
            "corpus_docs": corpus_docs,
            "corpus_metadatas": corpus_metadatas
        }
        
        with open(cache_path, "wb") as f:
            pickle.dump(cache_data, f)
            
        self._memory_cache[tenant_id] = cache_data
        logger.info(f"Successfully rebuilt and cached BM25 index for {tenant_id} ({len(corpus_docs)} chunks)")

    def get_index(self, tenant_id: str = "global") -> Tuple[Optional[BM25Okapi], List[str], List[str], List[Dict[str, Any]]]:
        """Gets the BM25 index and corpus details from memory or disk. Rebuilds if entirely missing."""
        if tenant_id in self._memory_cache:
            data = self._memory_cache[tenant_id]
            return data["bm25"], data["corpus_ids"], data["corpus_docs"], data["corpus_metadatas"]
            
        cache_path = self._get_cache_path(tenant_id)
        if os.path.exists(cache_path):
            logger.info(f"Loading BM25 index from disk for {tenant_id}")
            try:
                with open(cache_path, "rb") as f:
                    data = pickle.load(f)
                self._memory_cache[tenant_id] = data
                return data["bm25"], data["corpus_ids"], data["corpus_docs"], data["corpus_metadatas"]
            except Exception as e:
                logger.error(f"Failed to load BM25 index from disk: {e}")
                
        # If not in memory and not on disk, rebuild it.
        self.rebuild_index(tenant_id)
        if tenant_id in self._memory_cache:
            data = self._memory_cache[tenant_id]
            return data["bm25"], data["corpus_ids"], data["corpus_docs"], data["corpus_metadatas"]
            
        return None, [], [], []

bm25_manager = BM25Manager()
