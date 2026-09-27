from __future__ import annotations

import sys
import time
from pathlib import Path

from app.rag.document_builder import KnowledgeDocumentBuilder
from app.rag.knowledge_base import DEFAULT_STORE_PATH, LocalVectorStore


def build_knowledge_base(output_path: Path | str | None = None) -> LocalVectorStore:
    """
    Builds and persists the full hybrid knowledge base (products and suppliers).
    """
    start_time = time.perf_counter()
    print("Starting Knowledge Base construction...")

    builder = KnowledgeDocumentBuilder()

    # 1. Load source data and build documents
    print("Generating product and supplier summaries...")
    documents = builder.build_all_documents()

    product_count = sum(1 for d in documents if d.doc_type == "product")
    supplier_count = sum(1 for d in documents if d.doc_type == "supplier")
    total_count = len(documents)

    # 2. Build local vector store
    print("Vectorizing documents and building index...")
    store_path = Path(output_path or DEFAULT_STORE_PATH)
    store = LocalVectorStore(store_path=store_path)
    store.build_index(documents)

    # 3. Persist vector store
    print(f"Persisting vector store to {store_path}...")
    saved_path = store.persist(store_path)

    elapsed = round(time.perf_counter() - start_time, 2)

    # Required output format
    print("\n==========================================")
    print("KNOWLEDGE BASE BUILD REPORT")
    print("==========================================")
    print(f"Products indexed: {product_count}")
    print(f"Suppliers indexed: {supplier_count}")
    print(f"Total documents: {total_count}")
    print(f"Vector store: {saved_path}")
    print(f"Build time: {elapsed}s")
    print("Status: SUCCESS")
    print("==========================================\n")

    return store


if __name__ == "__main__":
    build_knowledge_base()
