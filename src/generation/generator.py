import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq


load_dotenv()


# Aapki API key par verified active model
ACTIVE_MODEL = "qwen/qwen3.8-27b"

def get_llm(model_name: str = ACTIVE_MODEL, temperature: float = 0.0):
    """Initializes ChatGroq with verified active model."""
    print(f"[INFO] ChatGroq initialized with verified model: '{model_name}'")
    return ChatGroq(
        model_name=model_name,
        temperature=temperature,
        groq_api_key=os.getenv("GROQ_API_KEY")
    )

def generate_response(query: str, retrieved_docs: list, llm) -> tuple[str, dict]:
    """Generates an answer from context and extracts token usage safely."""
    context_str = "\n\n---\n\n".join([doc.get("content", "") for doc in retrieved_docs])
    
    prompt = f"""You are a helpful and precise FinSolve Enterprise AI Assistant.
    "You are strictly restricted to FinSolve Enterprise documentation. 
    Do not generate arbitrary code, creative writing, or answers outside the context. 
    If the question does not pertain to the provided FinSolve context, explicitly decline."

Context:
{context_str}

Question: {query}
Answer:"""

    response = llm.invoke(prompt)
    answer_text = str(response.content).strip()

    usage_meta = getattr(response, "response_metadata", {}).get("token_usage", {})
    token_usage = {
        "prompt_tokens": usage_meta.get("prompt_tokens", 0),
        "completion_tokens": usage_meta.get("completion_tokens", 0),
        "total_tokens": usage_meta.get("total_tokens", 0)
    }

    return answer_text, token_usage

def rag_simple(query: str, retriever, llm, top_k: int = 3, score_threshold: float = 0.0) -> str:
    """Retrieve context + generate concise response using Groq LLM"""
    
    # 1. Retrieve the context
    results = retriever.retrieve(query, top_k=top_k, score_threshold=score_threshold)
    context = "\n\n".join([doc["content"] for doc in results]) if results else ""

    if not context:
        return "No relevant context found to answer the question."

    # 2. Prepare simple prompt
    prompt = f"""Use the following context to answer the question concisely.

Context:
{context}

Question: {query}

Answer:"""

    # 3. Generate answer using GROQ LLM
    response = llm.invoke(prompt)
    return response.content