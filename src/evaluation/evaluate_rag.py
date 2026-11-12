import os
import sys
import json
import warnings
from pathlib import Path
import pandas as pd
from datasets import Dataset
import sys
import types
import os
from groq import Groq

# --- FIX LANGCHAIN VERTEXAI DELETED PATH ---
try:
    import langchain_community.chat_models
    fake_vertex = types.ModuleType("langchain_community.chat_models.vertexai")
    fake_vertex.ChatVertexAI = None
    sys.modules["langchain_community.chat_models.vertexai"] = fake_vertex
except Exception:
    pass
# -------------------------------------------

# Suppress minor deprecation notices
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Setup root path resolution
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Ragas core imports
from ragas import evaluate
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall
)
from langchain_huggingface import HuggingFaceEmbeddings

# Project module imports
from src.embeddings.embedder import Embedder
from src.vector_store.chroma_client import ChromaManager
from src.retrieval.retriever import RAGRetriever, expand_query_with_llm
from src.retrieval.reranker import RAGReranker
from src.generation.generator import get_llm, generate_response


def run_ragas_evaluation():
    print("=" * 60)
    print("🚀 STARTING FINSOLE RAG BENCHMARK EVALUATION (STAGE 4)")
    print("=" * 60)

    # 1. Load Components
    print("\n[1/4] Loading embeddings, vector store, reranker, and Groq LLM...")
    embedder = Embedder(model_name="all-MiniLM-L6-v2")
    vector_store = ChromaManager(
        persist_dir=str(ROOT_DIR / "data" / "chroma_db"), 
        collection_name="company_docs"
    )
    retriever = RAGRetriever(vector_store=vector_store, embedding_manager=embedder)
    reranker = RAGReranker(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
    # 1. Fetch available Groq model automatically
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    available_models = [m.id for m in groq_client.models.list().data if "whisper" not in m.id]
    print(f"[INFO] Available Groq Models: {available_models}")

    # Pick the best active chat model available in your account
    preferred_models = [
        "llama-3.2-3b-preview",
        "llama-3.2-1b-preview",
        "llama-3.1-70b-versatile",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
        "llama3-8b-8192",
        "llama3-70b-8192"
    ]
    chosen_model = next((m for m in preferred_models if m in available_models), available_models[0])
    print(f"[INFO] Using verified model: '{chosen_model}'")

    base_llm = get_llm(model_name=chosen_model)

    # 2. Setup Ragas LLM and Embeddings wrappers
    ragas_llm = LangchainLLMWrapper(base_llm)
    hf_emb = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    ragas_embeddings = LangchainEmbeddingsWrapper(hf_emb)

    # Bind explicit LLM & Embeddings to all 4 metrics
    eval_metrics = [faithfulness, answer_relevancy, context_precision, context_recall]
    for metric in eval_metrics:
        metric.llm = ragas_llm
        if hasattr(metric, "embeddings"):
            metric.embeddings = ragas_embeddings

    # 3. Load Dataset
    dataset_path = ROOT_DIR / "data" / "evaluation" / "eval_dataset.json"
    if not dataset_path.exists():
        print(f"[ERROR] Evaluation file not found at: {dataset_path}")
        return

    with open(dataset_path, "r", encoding="utf-8") as f:
        eval_data = json.load(f)

    questions = []
    answers = []
    contexts = []
    ground_truths = []

    print(f"\n[2/4] Running RAG pipeline across {len(eval_data)} benchmark questions...")

    for idx, item in enumerate(eval_data, start=1):
        q = item["question"]
        gt = item["ground_truth"]

        print(f"\n[{idx}/{len(eval_data)}] Testing: '{q}'")
        
        # Query Expansion
        search_query = expand_query_with_llm(q, base_llm)
        
        # Dense Retrieval from ChromaDB
        initial_chunks = retriever.retrieve(query=search_query, top_k=25, score_threshold=-1.0)
        
        # Cross-Encoder Reranking
        best_chunks = reranker.rerank(query=search_query, retrieved_docs=initial_chunks, top_k=4)
        
        # Response Synthesis
        pred_answer = generate_response(query=q, retrieved_docs=best_chunks, llm=base_llm)

        questions.append(q)
        ground_truths.append(gt)
        answers.append(pred_answer)
        contexts.append([doc["content"] for doc in best_chunks])

    # 4. Prepare Evaluation Dataset
    print("\n[3/4] Preparing HuggingFace Dataset structure...")
    eval_dict = {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths
    }
    dataset = Dataset.from_dict(eval_dict)

    # 5. Execute Evaluation
    print("\n[4/4] Computing Ragas evaluation metrics (Faithfulness, Relevancy, Precision, Recall)...")
    results = evaluate(
        dataset=dataset,
        metrics=eval_metrics,
        llm=ragas_llm,
        embeddings=ragas_embeddings
    )

    print("\n" + "=" * 60)
    print("📊 RAGAS EVALUATION REPORT CARD")
    print("=" * 60)
    print(results)

    # Save to CSV
    output_dir = ROOT_DIR / "data" / "evaluation"
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_file = output_dir / "ragas_results.csv"
    
    df_results = results.to_pandas()
    df_results.to_csv(csv_file, index=False)
    print(f"\n✅ Detailed score table saved to: {csv_file}")


if __name__ == "__main__":
    run_ragas_evaluation()