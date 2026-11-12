from typing import List, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_documents(
    documents: List[Any],
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> List[Any]:
    """
    Splits text/markdown/PDF documents into chunks, 
    par CSV rows ko intact (bina tode) rakhta hai.
    """
    text_docs = []
    csv_docs = []

    # Alag karein: Prose documents vs CSV row documents
    for doc in documents:
        source = doc.metadata.get("source", "").lower()
        if source.endswith(".csv"):
            csv_docs.append(doc)
        else:
            text_docs.append(doc)

    print(f"[DEBUG] Chunking {len(text_docs)} text documents (size={chunk_size}, overlap={chunk_overlap})...")
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    chunked_text = text_splitter.split_documents(text_docs)

    # Dono ko merge karein
    all_chunks = chunked_text + csv_docs
    print(f"[DEBUG] Total chunks: {len(all_chunks)} ({len(chunked_text)} text chunks + {len(csv_docs)} intact CSV rows)")

    for idx, chunk in enumerate(all_chunks):
        chunk.metadata["chunk_id"] = idx

    return all_chunks