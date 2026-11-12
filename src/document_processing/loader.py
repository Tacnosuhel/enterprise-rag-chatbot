from pathlib import Path
from typing import List
import pandas as pd
from langchain_core.documents import Document

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader
)
from langchain_community.document_loaders.excel import UnstructuredExcelLoader


def load_csv_as_semantic_docs(file_path: Path) -> List[Document]:
    """
    Har CSV row ko structured Key-Value document me convert karta hai.
    Iski wajah se table ki columns aur values aapas me judi rehti hain.
    """
    docs = []
    try:
        df = pd.read_csv(file_path)
        df = df.dropna(how="all")

        for idx, row in df.iterrows():
            lines = [f"{col.strip()}: {str(val).strip()}" for col, val in row.items() if pd.notna(val)]
            content = "\n".join(lines)

            metadata = {
                "source": str(file_path),
                "row_index": idx
            }
            docs.append(Document(page_content=content, metadata=metadata))

        print(f"[DEBUG] Loaded {len(docs)} row-documents from CSV: {file_path}")
    except Exception as e:
        print(f"[ERROR] Failed to load CSV {file_path}: {e}")

    return docs


def load_all_documents(data_dir: str) -> List[Document]:
    """
    Load all supported files recursively from data directory.
    Supported: PDF, MD, TXT, CSV, XLSX, DOCX
    """
    data_path = Path(data_dir).resolve()
    print(f"[DEBUG] Data path: {data_path}")

    if not data_path.exists():
        raise FileNotFoundError(f"Data directory not found: {data_path}")

    documents = []

    # PDF files
    pdf_files = list(data_path.glob("**/*.pdf"))
    print(f"[DEBUG] Found {len(pdf_files)} PDF files")
    for pdf_file in pdf_files:
        print(f"[DEBUG] Loading PDF: {pdf_file}")
        try:
            loader = PyPDFLoader(str(pdf_file))
            documents.extend(loader.load())
        except Exception as e:
            print(f"[ERROR] Failed to load PDF {pdf_file}: {e}")

    # Markdown files
    md_files = list(data_path.glob("**/*.md"))
    print(f"[DEBUG] Found {len(md_files)} MD files")
    for md_file in md_files:
        print(f"[DEBUG] Loading MD: {md_file}")
        try:
            loader = TextLoader(str(md_file), encoding="utf-8")
            documents.extend(loader.load())
        except Exception as e:
            print(f"[ERROR] Failed to load MD {md_file}: {e}")

    # TXT files
    txt_files = list(data_path.glob("**/*.txt"))
    print(f"[DEBUG] Found {len(txt_files)} TXT files")
    for txt_file in txt_files:
        print(f"[DEBUG] Loading TXT: {txt_file}")
        try:
            loader = TextLoader(str(txt_file), encoding="utf-8")
            documents.extend(loader.load())
        except Exception as e:
            print(f"[ERROR] Failed to load TXT {txt_file}: {e}")

    # CSV files (Using structured row loader)
    csv_files = list(data_path.glob("**/*.csv"))
    print(f"[DEBUG] Found {len(csv_files)} CSV files")
    for csv_file in csv_files:
        print(f"[DEBUG] Loading CSV: {csv_file}")
        loaded_csv_docs = load_csv_as_semantic_docs(csv_file)
        documents.extend(loaded_csv_docs)

    # Excel files
    xlsx_files = list(data_path.glob("**/*.xlsx"))
    print(f"[DEBUG] Found {len(xlsx_files)} Excel files")
    for xlsx_file in xlsx_files:
        print(f"[DEBUG] Loading Excel: {xlsx_file}")
        try:
            loader = UnstructuredExcelLoader(str(xlsx_file))
            documents.extend(loader.load())
        except Exception as e:
            print(f"[ERROR] Failed to load Excel {xlsx_file}: {e}")

    # Word files
    docx_files = list(data_path.glob("**/*.docx"))
    print(f"[DEBUG] Found {len(docx_files)} Word files")
    for docx_file in docx_files:
        print(f"[DEBUG] Loading Word: {docx_file}")
        try:
            loader = Docx2txtLoader(str(docx_file))
            documents.extend(loader.load())
        except Exception as e:
            print(f"[ERROR] Failed to load DOCX {docx_file}: {e}")

    # Add department metadata safely

    for doc in documents:
        source_str = doc.metadata.get("source", "")
        if source_str:
            try:
                # Convert to Path and get parts relative to data_path
                source_path = Path(source_str).resolve()
                rel_parts = source_path.relative_to(data_path).parts
                # First folder under data/raw is the department
                doc.metadata["department"] = rel_parts[0].lower().strip()
            except Exception:
                doc.metadata["department"] = "general"
        else:
            doc.metadata["department"] = "general"