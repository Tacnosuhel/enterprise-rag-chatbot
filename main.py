import os
from src.embeddings.embedder import Embedder
from src.vector_store.chroma_client import ChromaManager
from src.retrieval.retriever import RAGRetriever
from src.retrieval.reranker import RAGReranker
from src.generation.generator import get_llm, rag_simple , generate_response
from sentence_transformers import SentenceTransformer


def main():
    chroma_path = "data/chroma_db"
    if not os.path.exists(chroma_path):
        print("[ERROR] ChromaDB not found! Please run 'uv run python ingest.py' first.")
        return

    print("=== INITIALIZING ADVANCED RAG PIPELINE ===")
    
    # 1. Load components
    embedder = Embedder(model_name="all-MiniLM-L6-v2")
    vector_store = ChromaManager(persist_dir=chroma_path, collection_name="company_docs")
    retriever = RAGRetriever(vector_store=vector_store, embedding_manager=embedder)
    reranker = RAGReranker(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
    llm = get_llm(model_name="qwen/qwen3.8-27b")

    # 2. Query
    query = "Which employees in the Technology department have a performance rating of 5, and what are their names, roles, and locations?"
    print(f"\nUser Query: {query}\n")

    # Step A: Retrieve 6 chunks from ChromaDB
    initial_chunks = retriever.retrieve(query=query, top_k=30, score_threshold=-1.0)
    print(f"[DEBUG] Total initial chunks retrieved: {len(initial_chunks)}")

    # Step B: Rerank and filter down to top 3
    best_chunks = reranker.rerank(query=query, retrieved_docs=initial_chunks, top_k=3)
    print(f"[DEBUG] Best chunks count after reranking: {len(best_chunks)}")

    # Display reranked scores
    print("\n--- Top Reranked Chunks ---")
    for doc in best_chunks:
        print(f"Rank {doc['rerank_rank']} | Score: {doc['rerank_score']:.4f} | Source: {doc['metadata'].get('source')}")

    # Step C: Send best context to LLM
    answer = generate_response(query=query, retrieved_docs=best_chunks, llm=llm)
    
    # Simple direct generation using best_chunks:
    context = "\n\n".join([doc["content"] for doc in best_chunks])
    prompt = f"Use the following context to answer concisely.\n\nContext:\n{context}\n\nQuestion: {query}\n\nAnswer:"
    answer = llm.invoke(prompt).content

    print("\n=== FINAL ANSWER ===")
    print(answer)


if __name__ == "__main__":
    main()