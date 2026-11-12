import os
import chromadb
from typing import List, Any, Dict
import numpy as np


class ChromaManager:
    def __init__(
        self,
        persist_dir: str = "data/chroma_db",
        collection_name: str = "company_docs"
    ):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        os.makedirs(self.persist_dir, exist_ok=True)

        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name
        )
        print(f"[INFO] Connected to ChromaDB at '{self.persist_dir}' | Collection: '{self.collection_name}'")

    def add_documents(self, chunks: List[Any], embeddings: np.ndarray) -> None:
        """Stores chunk contents, department/source metadata, and vectors."""
        ids = [f"chunk_{i}" for i in range(len(chunks))]
        documents = [chunk.page_content for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]
        embeddings_list = embeddings.tolist()

        print(f"[INFO] Ingesting {len(chunks)} records into ChromaDB...")
        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings_list
        )
        print(f"[INFO] Upsert complete. Total stored chunks: {self.collection.count()}")

    def query(self, query_embedding: List[float], top_k: int = 3) -> Dict[str, Any]:
        """Vector similarity search against precomputed query embedding."""
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )