# Reranking retrieved chunks
from typing import List, Dict, Any
from sentence_transformers import CrossEncoder


class RAGReranker:
    """Uses a Cross-Encoder to re-rank retrieved documents by true semantic relevance."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        print(f"[INFO] Loading Reranker model: {model_name}...")
        self.model = CrossEncoder(model_name)
        print("[INFO] Reranker model loaded successfully.")

    def rerank(
        self, query: str, retrieved_docs: List[Dict[str, Any]], top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Reranks retrieved chunks and returns the top_k most relevant ones.
        """
        if not retrieved_docs:
            print("[INFO] No documents to rerank.")
            return []

        print(f"[INFO] Reranking {len(retrieved_docs)} documents for query: '{query}'")

        # 1. Prepare pairs: (Query, Chunk Content)
        pairs = [[query, doc["content"]] for doc in retrieved_docs]

        # 2. Predict relevance scores using Cross-Encoder
        scores = self.model.predict(pairs)

        # 3. Attach rerank score to each doc
        for idx, score in enumerate(scores):
            retrieved_docs[idx]["rerank_score"] = float(score)

        # 4. Sort documents by score in descending order (highest score first)
        reranked_docs = sorted(
            retrieved_docs, key=lambda x: x["rerank_score"], reverse=True
        )

        # 5. Take top_k and update rank
        final_docs = reranked_docs[:top_k]
        for new_rank, doc in enumerate(final_docs, start=1):
            doc["rerank_rank"] = new_rank

        print(f"[INFO] Rerank complete. Returning top {len(final_docs)} chunks.")
        return final_docs