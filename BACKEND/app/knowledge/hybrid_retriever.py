import logging
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
import nltk

# Ensure nltk punkt is downloaded for tokenization
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt', quiet=True)
    nltk.download('punkt_tab', quiet=True)

from app.knowledge.vector_store import vector_store
from app.knowledge.bm25_manager import bm25_manager

logger = logging.getLogger(__name__)

from app.core.config import settings

class HybridRetriever:
    def __init__(self):
        # We could cache BM25 indices here, keyed by tenant_id or document_id
        self._bm25_cache = {}
        self._corpus_cache = {}

    def search(self, query: str, query_embedding: List[float], n_results: int = 10, where: Optional[Dict[str, Any]] = None, predicted_domains: Dict[str, float] = None, document_type_priority: str = "any") -> List[Dict[str, Any]]:
        # 1. Dense Retrieval (ChromaDB) - Broaden to Top 12 (reduced for latency)
        initial_k = max(12, int(n_results * 1.5))
        dense_results = vector_store.search(query_embedding, n_results=initial_k, where=where)
        
        # 2. Fetch corpus and BM25 index from Manager
        tenant_id = "global"
        if where:
            if "tenant_id" in where:
                tenant_id = where["tenant_id"]
            elif "$and" in where:
                for cond in where["$and"]:
                    if "tenant_id" in cond:
                        tenant_id = cond["tenant_id"]
                        break

        bm25, corpus_ids, corpus_docs, corpus_metadatas = bm25_manager.get_index(tenant_id)
        
        if not bm25 or not corpus_docs:
            return dense_results[:n_results]

        tokenized_query = nltk.word_tokenize(query.lower())
        
        # Get BM25 scores
        bm25_scores = bm25.get_scores(tokenized_query)
        
        # 3. Reciprocal Rank Fusion (RRF) with Metadata Bonus
        rrf_scores = {}
        predicted_domains = predicted_domains or {}
        
        # Helper to calculate metadata bonus
        def calculate_metadata_bonus(metadata: Dict[str, Any]) -> float:
            bonus = 0.0
            
            # Domain Match Bonus (Proportional to LLM confidence)
            chunk_domain = metadata.get("legal_domain", "")
            if chunk_domain in predicted_domains:
                bonus += 0.025 * predicted_domains[chunk_domain]
                
            # Document Type Bonus
            chunk_type = metadata.get("document_type", "")
            if document_type_priority != "any" and chunk_type == document_type_priority:
                bonus += 0.015
                
            # Act Name Keyword Match
            act_name = metadata.get("act_name", "").lower()
            if act_name:
                act_words = set(act_name.split())
                query_words = set(query.lower().split())
                # If significant overlap, boost (e.g. "penal code")
                if len(act_words.intersection(query_words)) >= 2:
                    bonus += 0.02
                    
            return bonus
        
        # Rank Dense
        for rank, res in enumerate(dense_results):
            chunk_id = res["id"]
            base_rrf = (1.0 / (60 + rank))
            bonus = calculate_metadata_bonus(res["metadata"])
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + base_rrf + bonus
            
        # Rank Sparse
        sparse_ranking = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)
        for rank, idx in enumerate(sparse_ranking[:20]):
            chunk_id = corpus_ids[idx]
            base_rrf = (1.0 / (60 + rank))
            
            # Avoid double-counting the bonus if it was already seen in dense
            if chunk_id not in rrf_scores:
                bonus = calculate_metadata_bonus(corpus_metadatas[idx])
                rrf_scores[chunk_id] = base_rrf + bonus
            else:
                rrf_scores[chunk_id] += base_rrf
            
        # 4. Sort and apply Confidence Threshold
        sorted_rrf = sorted(rrf_scores.items(), key=lambda item: item[1], reverse=True)
        
        threshold = getattr(settings, "MIN_RETRIEVAL_THRESHOLD", 0.015)
        filtered_ids = [item[0] for item in sorted_rrf if item[1] >= threshold]
        
        # Take up to n_results
        top_ids = filtered_ids[:n_results]
        
        # Reconstruct the final list of dicts
        final_results = []
        for rank, cid in enumerate(top_ids):
            found_dense = None
            for res in dense_results:
                if res["id"] == cid:
                    found_dense = res
                    break
            
            is_sparse = False
            for idx in sparse_ranking[:20]:
                if corpus_ids[idx] == cid:
                    is_sparse = True
                    break
            
            retrieval_method = "hybrid" if (found_dense and is_sparse) else "dense" if found_dense else "sparse"
            
            if found_dense:
                found_dense["metadata"]["retrieval_method"] = retrieval_method
                found_dense["metadata"]["retrieval_rank"] = rank + 1
                found_dense["metadata"]["rrf_score"] = rrf_scores[cid]
                final_results.append(found_dense)
            else:
                idx = corpus_ids.index(cid)
                final_results.append({
                    "id": cid,
                    "document": corpus_docs[idx],
                    "metadata": {
                        **corpus_metadatas[idx],
                        "retrieval_method": retrieval_method,
                        "retrieval_rank": rank + 1,
                        "rrf_score": rrf_scores[cid]
                    },
                    "distance": 0.0 
                })
                
        return final_results

hybrid_retriever = HybridRetriever()
