# src/api/main.py
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from src.embeddings.embedder import Embedder
from src.vector_store.chroma_client import ChromaManager
from src.retrieval.retriever import RAGRetriever, expand_query_with_llm
from src.retrieval.reranker import RAGReranker
from src.generation.generator import get_llm, generate_response
from src.security.guardrails import guardrails
from src.security.jwt_auth import authenticate_user, create_access_token, get_current_user
from src.monitoring.logger import log_interaction
from src.api.schemas import (
    LoginRequest,
    LoginResponse,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    DocumentSource
)

# 1. Lifespan Manager (Load models ONCE at startup)
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n[STARTUP] Loading FinSolve RAG Pipeline components into memory...")
    embedder = Embedder(model_name="all-MiniLM-L6-v2")
    vector_store = ChromaManager(persist_dir="data/chroma_db", collection_name="company_docs")
    retriever = RAGRetriever(vector_store=vector_store, embedding_manager=embedder)
    reranker = RAGReranker(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
    llm = get_llm(model_name="qwen/qwen3.8-27b")

    app.state.embedder = embedder
    app.state.vector_store = vector_store
    app.state.retriever = retriever
    app.state.reranker = reranker
    app.state.llm = llm
    print("[STARTUP] All models and ChromaDB loaded successfully!\n")
    yield
    print("\n[SHUTDOWN] Releasing resources...")

app = FastAPI(
    title="FinSolve Enterprise RAG API",
    version="1.0.0",
    description="Production-grade secure RAG API with JWT Authentication, RBAC, and Guardrails",
    lifespan=lifespan
)

# 2. CORS (Cross-Origin Resource Sharing) for React/Frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 3. Health & Readiness Endpoint
@app.get("/health", response_model=HealthResponse, tags=["Monitoring"])
def health_check():
    """Liveness & readiness probe for container orchestrators (Kubernetes/Docker)."""
    return HealthResponse(
        status="healthy",
        chroma_db_connected=hasattr(app.state, "vector_store"),
        models_loaded=hasattr(app.state, "llm") and hasattr(app.state, "reranker")
    )


# 4. Authentication / Login Endpoint
@app.post("/auth/login", response_model=LoginResponse, tags=["Authentication"])
def login(payload: LoginRequest):
    """Authenticates user with username & password, returns signed JWT token."""
    user = authenticate_user(payload.username, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    token_data = {
        "sub": user["username"],
        "name": user.get("name", user["username"]),
        "role": user["role"],
        "allowed_departments": user["allowed_departments"]
    }
    token = create_access_token(data=token_data)

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        role=user["role"],
        allowed_departments=user["allowed_departments"]
    )


# 5. Core Secure RAG Chat Endpoint
@app.post("/v1/chat", response_model=ChatResponse, tags=["RAG Service"])
def chat(
    payload: ChatRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Main RAG pipeline:
    1. Input Guardrail & Prompt Injection Check
    2. Greeting / Small-talk Fast Path
    3. Domain Boundary Scope Check
    4. Query Intent Classification & Strict RBAC Check
    5. Query Expansion & ChromaDB Retrieval
    6. RBAC Document Filtering & Cross-Encoder Reranking
    7. LLM Generation & Output Sanitization
    8. Async Audit Logging
    """
    start_time = time.time()
    query = payload.query.strip()
    user_name = current_user.get("name", current_user.get("username", "User"))
    role = current_user["role"]
    allowed_depts = [d.lower().strip() for d in current_user["allowed_departments"]]
    is_admin = role.lower() == "admin" or "all" in allowed_depts

    # A. Guardrails: Prompt Injection Check
    is_safe, safety_msg = guardrails.validate_input(query)
    if not is_safe:
        latency = time.time() - start_time
        resp_text = f"Security Policy Violation: {safety_msg}"
        background_tasks.add_task(
            log_interaction,
            user=user_name,
            role=role,
            query=query,
            allowed_departments=allowed_depts,
            target_department="security_violation",
            retrieved_chunks=[],
            response=resp_text,
            latency_seconds=latency,
            status="SECURITY_VIOLATION"
        )
        return ChatResponse(
            query=query,
            answer=resp_text,
            user=user_name,
            role=role,
            status="SECURITY_VIOLATION",
            latency_seconds=round(latency, 2),
            token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            sources=[]
        )

    # B. Guardrails: Greeting / Conversational Fast Path
    if hasattr(guardrails, "is_greeting") and guardrails.is_greeting(query):
        latency = time.time() - start_time
        greeting_text = (
            f"Hello {user_name.capitalize()}! I am FinSolve's Enterprise Assistant. "
            f"How can I assist you with company documentation, policies, or specifications today?"
        )
        background_tasks.add_task(
            log_interaction,
            user=user_name,
            role=role,
            query=query,
            allowed_departments=allowed_depts,
            target_department="greeting",
            retrieved_chunks=[],
            response=greeting_text,
            latency_seconds=latency,
            status="SUCCESS"
        )
        return ChatResponse(
            query=query,
            answer=greeting_text,
            user=user_name,
            role=role,
            status="SUCCESS",
            latency_seconds=round(latency, 2),
            token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            sources=[]
        )

    # C. Guardrails: Domain Scope Check (Reject arbitrary coding/general chat)
    in_scope, scope_msg = guardrails.check_domain_scope(query)
    if not in_scope:
        latency = time.time() - start_time
        background_tasks.add_task(
            log_interaction,
            user=user_name,
            role=role,
            query=query,
            allowed_departments=allowed_depts,
            target_department="out_of_scope",
            retrieved_chunks=[],
            response=scope_msg,
            latency_seconds=latency,
            status="OUT_OF_SCOPE"
        )
        return ChatResponse(
            query=query,
            answer=scope_msg,
            user=user_name,
            role=role,
            status="OUT_OF_SCOPE",
            latency_seconds=round(latency, 2),
            token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            sources=[]
        )

    # D. Query-level Department Intent & Pre-emptive RBAC Check
    target_dept = guardrails.classify_department(query) if hasattr(guardrails, "classify_department") else "general"
    
    # Agar query explicitly kisi unauthorized department ki hai (e.g., Alice asking HR query)
    if not is_admin and target_dept != "general" and target_dept not in allowed_depts:
        latency = time.time() - start_time
        access_denied_msg = (
            f"Access Denied: Your role ({role.upper()}) is not authorized to access "
            f"{target_dept.upper()} documents. Permitted: {', '.join(allowed_depts)}."
        )
        background_tasks.add_task(
            log_interaction,
            user=user_name,
            role=role,
            query=query,
            allowed_departments=allowed_depts,
            target_department=target_dept,
            retrieved_chunks=[],
            response=access_denied_msg,
            latency_seconds=latency,
            status="ACCESS_DENIED"
        )
        return ChatResponse(
            query=query,
            answer=access_denied_msg,
            user=user_name,
            role=role,
            status="ACCESS_DENIED",
            latency_seconds=round(latency, 2),
            token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            sources=[]
        )

    # E. Retrieval
    retriever: RAGRetriever = app.state.retriever
    reranker: RAGReranker = app.state.reranker
    llm = app.state.llm

    search_query = expand_query_with_llm(query, llm)
    initial_chunks = retriever.retrieve(query=search_query, top_k=30, score_threshold=-1.0)

    # F. RBAC Document Filtering
    filtered_chunks = []
    for chunk in initial_chunks:
        chunk_dept = str(chunk.get("metadata", {}).get("department", "")).lower().strip()
        if is_admin or chunk_dept in allowed_depts or chunk_dept == "general":
            filtered_chunks.append(chunk)

    token_stats = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    best_chunks = []
    sources = []

    if filtered_chunks:
        best_chunks = reranker.rerank(query=search_query, retrieved_docs=filtered_chunks, top_k=6)
        
        # Out-of-Domain Catch: Rerank relevance check
        if best_chunks and best_chunks[0].get("rerank_score", 0.0) < -5.0:
            status_code = "OUT_OF_DOMAIN_REJECTED"
            answer = "The query does not match any relevant FinSolve enterprise documentation."
        else:
            status_code = "SUCCESS"
            raw_answer, token_stats = generate_response(query=query, retrieved_docs=best_chunks, llm=llm)
            answer = guardrails.mask_pii_output(raw_answer)

            for doc in best_chunks:
                sources.append(
                    DocumentSource(
                        source=str(doc.get("metadata", {}).get("source", "Unknown")),
                        department=str(doc.get("metadata", {}).get("department", "Unknown")),
                        rerank_score=round(float(doc.get("rerank_score", 0.0)), 4)
                    )
                )
    else:
        status_code = "NO_CONTEXT_PERMITTED"
        answer = f"Access Denied: No permitted documents found for departments: {', '.join(allowed_depts)}."

    latency = time.time() - start_time

    # G. Non-blocking Asynchronous Background Logging
    background_tasks.add_task(
        log_interaction,
        user=user_name,
        role=role,
        query=query,
        allowed_departments=allowed_depts,
        target_department=target_dept,
        retrieved_chunks=best_chunks,
        response=answer,
        latency_seconds=latency,
        token_usage=token_stats,
        status=status_code
    )

    return ChatResponse(
        query=query,
        answer=answer,
        user=user_name,
        role=role,
        status=status_code,
        latency_seconds=round(latency, 2),
        token_usage=token_stats,
        sources=sources
    )