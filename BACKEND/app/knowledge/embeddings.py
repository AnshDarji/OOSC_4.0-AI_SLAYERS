import logging
from typing import List
from sentence_transformers import SentenceTransformer
import torch

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        self.model_name = "BAAI/bge-base-en-v1.5"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # Defer loading the model until it's actually required. This prevents
        # the application from attempting to download large models at import
        # time (which fails when behind an authenticated proxy).
        logger.info(f"Embedding service initialized (model loading deferred). device={self.device}")
        self.model = None
        
    def warmup(self):
        """Force model loading into memory during startup."""
        if self.model is None:
            logger.info(f"Warming up embedding model {self.model_name} on {self.device}...")
            self.model = SentenceTransformer(self.model_name, device=self.device)
            logger.info("Embedding model warmed up successfully.")
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        if not texts:
            return []
        try:
            # Lazy-load model if needed
            if self.model is None:
                logger.info(f"Loading embedding model {self.model_name} on {self.device}...")
                self.model = SentenceTransformer(self.model_name, device=self.device)
                logger.info("Embedding model loaded successfully.")

            # sentence_transformers encodes batches efficiently under the hood
            # normalize_embeddings=True is recommended for BGE models
            embeddings = self.model.encode(texts, normalize_embeddings=True)
            return embeddings.tolist()

        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise e
            
    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a single query."""
        # BGE models use a specific prefix for queries to improve retrieval
        prefix = "Represent this sentence for searching relevant passages: "
        prefixed_query = prefix + query
        results = self.embed_texts([prefixed_query])
        if results and len(results) > 0:
            return results[0]
        return []

embedding_service = EmbeddingService()
