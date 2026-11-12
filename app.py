# app.py
import os
import time
from pathlib import Path
import streamlit as st

from src.security.auth import USER_PROFILES, get_user_permissions
from src.embeddings.embedder import Embedder
from src.vector_store.chroma_client import ChromaManager
from src.retrieval.retriever import RAGRetriever, expand_query_with_llm
from src.retrieval.reranker import RAGReranker
from src.generation.generator import get_llm, generate_response
from src.security.guardrails import guardrails
from src.monitoring.logger import log_interaction

st.set_page_config(page_title="FinSolve Enterprise Assistant", layout="wide")

# 1. Resource Caching (Load models only once)
@st.cache_resource
def load_rag_components():
    embedder = Embedder(model_name="all-MiniLM-L6-v2")
    vector_store = ChromaManager(persist_dir="data/chroma_db", collection_name="company_docs")
    retriever = RAGRetriever(vector_store=vector_store, embedding_manager=embedder)
    reranker = RAGReranker(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
    llm = get_llm()
    return embedder, vector_store, retriever, reranker, llm

embedder, vector_store, retriever, reranker, llm = load_rag_components()

# 2. Sidebar: User / Role Selection
st.sidebar.title("🔐 Access Control (RBAC)")

user_keys = list(USER_PROFILES.keys())
selected_user_key = st.sidebar.selectbox(
    "Select Active User / Role:",
    user_keys,
    format_func=lambda k: USER_PROFILES[k]["name"]
)

user_info = get_user_permissions(selected_user_key)

st.sidebar.markdown(f"**Current Role:** `{user_info['role'].upper()}`")
st.sidebar.markdown("**Permitted Departments:**")
for dept in user_info["allowed_departments"]:
    st.sidebar.markdown(f"- 📁 `{dept}`")

# 3. Main Chat Interface
st.title("🏢 FinSolve Enterprise Assistant")
st.caption(f"Logged in as: **{user_info['name']}**")

# Manage Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous chats
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User Input
if prompt := st.chat_input("Ask a question about FinSolve policies, architecture, or data..."):
    # START TIME DEFINED AT THE VERY TOP OF INPUT
    start_time = time.time()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # Default tracking state
        token_stats = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        best_chunks = []
        filtered_chunks = []
        initial_chunks = []
        primary_target_dept = None
        status = "SUCCESS"
        answer = ""

        # Step 1: Input Guardrail Check
        is_safe, safety_msg = guardrails.validate_input(prompt)

        if not is_safe:
            status = "SECURITY_VIOLATION"
            answer = f"🛡️ **Security Policy Violation:** {safety_msg}"
            st.error(answer)
        else:
            with st.spinner("Processing through secure RAG pipeline..."):
                # Query expansion
                search_query = expand_query_with_llm(prompt, llm)

                # Retrieval
                initial_chunks = retriever.retrieve(query=search_query, top_k=30, score_threshold=-1.0)

                # RBAC Filtering
                allowed_depts = [d.lower().strip() for d in user_info["allowed_departments"]]
                is_admin = user_info["role"].lower() == "admin"

                for chunk in initial_chunks:
                    chunk_dept = str(chunk.get("metadata", {}).get("department", "")).lower().strip()
                    if is_admin or chunk_dept in allowed_depts:
                        filtered_chunks.append(chunk)

                top_initial_depts = [
                    str(c.get("metadata", {}).get("department", "")).lower().strip()
                    for c in initial_chunks[:5]
                ]
                primary_target_dept = max(set(top_initial_depts), key=top_initial_depts.count) if top_initial_depts else None

                # Policy Enforcement
                if not is_admin and primary_target_dept and primary_target_dept not in allowed_depts:
                    status = "ACCESS_DENIED"
                    answer = (
                        f"🔒 **Access Denied:** Your role (`{user_info['role'].upper()}`) is not authorized "
                        f"to access `{primary_target_dept.upper()}` documents. "
                        f"Permitted departments: `{', '.join(allowed_depts)}`."
                    )
                elif filtered_chunks:
                    best_chunks = reranker.rerank(query=search_query, retrieved_docs=filtered_chunks, top_k=6)
                    raw_answer, token_stats = generate_response(query=prompt, retrieved_docs=best_chunks, llm=llm)
                    answer = guardrails.mask_pii_output(raw_answer)
                else:
                    status = "NO_CONTEXT_PERMITTED"
                    answer = (
                        f"🔒 **Access Denied:** No permitted documents found. "
                        f"Your role only has access to: `{', '.join(allowed_depts)}`."
                    )

                st.markdown(answer)

                # Audit Diagnostics Expander
                with st.expander("🔍 Security & Audit Logs"):
                    st.write("**Input Validation:** ✅ Passed")
                    st.write(f"**RBAC Check:** Allowed {len(filtered_chunks)}/{len(initial_chunks)} Chunks")
                    st.write(f"**Tokens:** Total `{token_stats.get('total_tokens', 0)}` (Prompt: `{token_stats.get('prompt_tokens', 0)}`, Completion: `{token_stats.get('completion_tokens', 0)}`)")
                    if best_chunks:
                        for doc in best_chunks:
                            st.caption(f"Source: `{doc['metadata'].get('source')}` | Score: `{doc.get('rerank_score', 0):.4f}`")

        # Compute Latency safely
        latency = time.time() - start_time

        # Silent Background Logging
        log_interaction(
            user=user_info.get("name", "Unknown"),
            role=user_info.get("role", "unknown"),
            query=prompt,
            allowed_departments=user_info.get("allowed_departments", []),
            target_department=primary_target_dept,
            retrieved_chunks=best_chunks,
            response=answer,
            latency_seconds=latency,
            token_usage=token_stats,
            status=status
        )

        st.session_state.messages.append({"role": "assistant", "content": answer})