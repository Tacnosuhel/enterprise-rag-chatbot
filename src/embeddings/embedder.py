from typing import List, Any
from sentence_transformers import SentenceTransformer
import numpy as np


class Embedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        print(f"[INFO] Initializing embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        print(f"[INFO] Loaded embedding model: {model_name}")

    def embed_chunks(self, chunks: List[Any]) -> np.ndarray:
        """Takes document chunks and returns a 2D numpy array of embeddings."""
        texts = [chunk.page_content for chunk in chunks]
        print(f"[INFO] Generating embeddings for {len(texts)} chunks...")
        embeddings = self.model.encode(texts, show_progress_bar=True)
        print(f"[INFO] Embeddings generated with shape: {embeddings.shape}")
        return embeddings

    def embed_query(self, query: str) -> List[float]:
        """Encodes a single user query into a list of floats for retrieval."""
        return self.model.encode(query).tolist()