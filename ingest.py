import os
import shutil
import json
from src.document_processing.loader import load_all_documents
from src.document_processing.chunker import chunk_documents
from src.embeddings.embedder import Embedder
from src.vector_store.chroma_client import ChromaManager

# Purana mix-up hatane ke liye shutil.rmtree() se data/chroma_db ko pehle hi wipe kar denge:
def clean_existing_db(chroma_dir: str = "data/chroma_db"):
    """Delete existing ChromaDB folder to avoid mixing stale data."""
    if os.path.exists(chroma_dir):
        print(f"[INFO] Removing old database at '{chroma_dir}'...")
        shutil.rmtree(chroma_dir)
        print("[INFO] Old database removed successfully.")


def save_processed_chunks(chunks, output_path: str = "data/processed/chunks.json"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    serialized = [
        {"page_content": c.page_content, "metadata": c.metadata}
        for c in chunks
    ]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(serialized, f, indent=2, ensure_ascii=False)
    print(f"[INFO] Saved {len(chunks)} chunks to '{output_path}'")


def run_ingestion():
    # 1. Clean old DB
    clean_existing_db("data/chroma_db")

    # 2. Load
    docs = load_all_documents("data/raw")
    if not docs:
        print("[WARNING] No documents found in data/raw.")
        return

    # 3. Chunk
    chunks = chunk_documents(docs, chunk_size=1000, chunk_overlap=200)

    # 4. Save cache
    save_processed_chunks(chunks, "data/processed/chunks.json")

    # 5. Embed & Persist
    embedder = Embedder(model_name="all-MiniLM-L6-v2")
    embeddings = embedder.embed_chunks(chunks)

    chroma_mgr = ChromaManager(persist_dir="data/chroma_db", collection_name="company_docs")
    chroma_mgr.add_documents(chunks, embeddings)

    print("=== INGESTION FINISHED FRESH & CLEAN ===")


if __name__ == "__main__":
    run_ingestion()