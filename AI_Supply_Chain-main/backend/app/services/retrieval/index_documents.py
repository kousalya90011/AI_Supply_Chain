from __future__ import annotations

import logging
import sys
import time

from app.services.retrieval.document_builder import KnowledgeDocumentBuilder
from app.services.retrieval.vector_store import LocalVectorStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("index_documents")


def run_indexing() -> None:
    """
    Executes the business-level knowledge document indexing pipeline.
    """
    print("=" * 70)
    print("AI-POWERED SUPPLY CHAIN CONTROL TOWER — KNOWLEDGE INDEXING PIPELINE")
    print("=" * 70)

    start_time = time.perf_counter()

    # 1. Initialize Document Builder & Build Chunks
    print("\n[Step 1/3] Extracting operational telemetry and generating business chunks...")
    builder = KnowledgeDocumentBuilder()
    chunks = builder.build_all_chunks()
    print(f"-> Generated {len(chunks)} business-level knowledge chunks.")

    # 2. Initialize Vector Store & Generate Embeddings
    print("\n[Step 2/3] Generating vector embeddings and indexing chunks...")
    vector_store = LocalVectorStore()
    stats = vector_store.build_index(chunks)

    # 3. Report Indexing Statistics
    elapsed = time.perf_counter() - start_time
    print("\n[Step 3/3] Indexing Complete!")
    print("-" * 50)
    print(f"Total Chunks Indexed : {stats.total_chunks}")
    print(f"Embedding Provider   : {stats.embedding_provider}")
    print(f"Vector Store Type    : {stats.vector_store_type}")
    print(f"Persistence Target   : {stats.store_path}")
    print(f"Total Pipeline Time  : {elapsed:.2f} seconds")
    print("-" * 50)
    print("Chunk Distribution by Document Type:")
    for doc_type, count in sorted(stats.chunks_by_type.items()):
        print(f"  * {doc_type:<28}: {count} chunks")
    print("\nChunk Distribution by Risk Level:")
    for risk, count in sorted(stats.chunks_by_risk.items()):
        print(f"  * {risk:<28}: {count} chunks")
    print("=" * 70)


if __name__ == "__main__":
    run_indexing()
