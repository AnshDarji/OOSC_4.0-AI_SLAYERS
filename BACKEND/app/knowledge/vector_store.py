import chromadb
from chromadb.config import Settings
import os
from typing import List, Dict, Any, Optional

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chroma_db")

class VectorStore:
    def __init__(self, collection_name: str = "nyaay_knowledge"):
        os.makedirs(DB_DIR, exist_ok=True)
        # Initialize ChromaDB client using PersistentClient for local storage
        self.client = chromadb.PersistentClient(path=DB_DIR, settings=Settings(anonymized_telemetry=False))
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        self.sc_collection = self.client.get_or_create_collection(
            name="supreme_court_cases",
            metadata={"hnsw:space": "cosine"}
        )

    def add_chunks(self, ids: List[str], embeddings: List[List[float]], documents: List[str], metadatas: List[Dict[str, Any]], target_collection: str = "nyaay_knowledge"):
        """Add vectorized chunks to the collection."""
        if not ids:
            return
            
        coll = self.collection if target_collection == "nyaay_knowledge" else self.sc_collection
        
        # Chroma API limits batch size
        batch_size = 500
        for i in range(0, len(ids), batch_size):
            coll.upsert(
                ids=ids[i:i + batch_size],
                embeddings=embeddings[i:i + batch_size],
                documents=documents[i:i + batch_size],
                metadatas=metadatas[i:i + batch_size]
            )

    def search(self, query_embedding: List[float], n_results: int = 5, where: Optional[Dict[str, Any]] = None, search_sc: bool = False) -> List[Dict[str, Any]]:
        """Search for the most similar chunks. Optionally include supreme_court_cases."""
        
        def do_search(coll, n, where_clause):
            # ChromaDB expects None, not an empty dict
            if where_clause == {}:
                where_clause = None
                
            # Pass where_clause to ChromaDB if it's not None
            try:
                res = coll.query(
                    query_embeddings=[query_embedding],
                    n_results=n,
                    where=where_clause,
                    include=["documents", "metadatas", "distances"]
                )
                formatted = []
                if res and res["ids"] and len(res["ids"]) > 0:
                    for i in range(len(res["ids"][0])):
                        formatted.append({
                            "id": res["ids"][0][i],
                            "document": res["documents"][0][i],
                            "metadata": res["metadatas"][0][i],
                            "distance": res["distances"][0][i]
                        })
                return formatted
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Retrieval failed for collection {coll.name} with where={where_clause}. Error: {e}")
                return []

        results = do_search(self.collection, n_results, where)
        
        if search_sc:
            # Drop where clause for SC collection since schema differs
            sc_where = None
            sc_results = do_search(self.sc_collection, n_results, sc_where)
            results.extend(sc_results)
            # Re-sort by distance (lower is better for cosine distance in Chroma)
            results.sort(key=lambda x: x["distance"])
            results = results[:n_results]
        
        return results
        
    def delete_by_metadata(self, where: Dict[str, Any]):
        """Delete documents matching specific metadata (e.g. document_id)."""
        self.collection.delete(where=where)

# Singleton instance for global access
vector_store = VectorStore()
