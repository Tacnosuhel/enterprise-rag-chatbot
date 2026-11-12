from typing import List, Dict, Any
from src.vector_store.chroma_client import ChromaManager
from src.embeddings.embedder import Embedder


class RAGRetriever:
    """Handles query-based retrieval from the vector store"""

    def __init__(self, vector_store: ChromaManager, embedding_manager: Embedder):
        """
        Initialize the retriever

        Args:
            vector_store: Vector store containing document embeddings (ChromaManager)
            embedding_manager: Manager for generating query embeddings (Embedder)
        """
        self.vector_store = vector_store
        self.embedding_manager = embedding_manager

    def retrieve(
        self, query: str, top_k: int = 5, score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents for a query

        Args:
            query: The search query
            top_k: Number of top results to return
            score_threshold: Minimum similarity score threshold

        Returns:
            List of dictionaries containing retrieved documents and metadata
        """
        print(f"Retrieving documents for query: '{query}'")
        print(f"Top K: {top_k}, Score threshold: {score_threshold}")

        # Generate query embedding
        query_embedding = self.embedding_manager.embed_query(query)

        # Search in vector store
        try:
            results = self.vector_store.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )

            # Process results
            retrieved_docs = []

            if results["documents"] and results["documents"][0]:
                documents = results["documents"][0]
                metadatas = results["metadatas"][0]
                distances = results["distances"][0]
                ids = results["ids"][0]

                for i, (doc_id, document, metadata, distance) in enumerate(
                    zip(ids, documents, metadatas, distances)
                ):
                    # Convert distance to similarity score (ChromaDB uses cosine distance)
                    similarity_score = 1 - distance

                    if similarity_score >= score_threshold:
                        retrieved_docs.append({
                            "id": doc_id,
                            "content": document,
                            "metadata": metadata,
                            "similarity_score": similarity_score,
                            "distance": distance,
                            "rank": i + 1,
                        })

                print(f"Retrieved {len(retrieved_docs)} documents (after filtering)")
            else:
                print("No documents found")

            return retrieved_docs

        except Exception as e:
            print(f"Error during retrieval: {e}")
            return []


def expand_query_with_llm(query: str, llm) -> str:
        """
        User query me se short acronyms aur context expand karta hai 
        taaki vector search accurate documents dhoondh sake.
        """
        prompt = f"""You are a search query optimizer for an enterprise documentation system.
        Rewrite the following user query by expanding all abbreviations, technical acronyms (e.g., RTO -> Recovery Time Objective, RPO -> Recovery Point Objective), and adding relevant search keywords.
        Output ONLY the rewritten search query with no explanations or pleasantries.

        User Query: {query}
        Optimized Search Query:"""

        try:
            response = llm.invoke(prompt)
            expanded = response.content.strip().replace('"', '')
            return expanded
        except Exception as e:
            print(f"[WARNING] Query expansion failed: {e}. Using original query.")
            return query