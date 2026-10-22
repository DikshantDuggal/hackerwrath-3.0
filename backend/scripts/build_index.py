"""
CLI script to build the persistent RAG vector index from train.jsonl.
Supports --force to rebuild index from scratch.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

# Ensure backend root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.rag.config import TRAIN_DATA_PATH, VECTOR_STORE_DIR
from app.rag.index_builder import VectorIndexBuilder


def main() -> None:
    parser = argparse.ArgumentParser(description="Build persistent vector index for RAG scam detection.")
    parser.add_argument(
        "--train-data",
        default=TRAIN_DATA_PATH,
        help="Path to training/reference JSONL dataset",
    )
    parser.add_argument(
        "--output-dir",
        default=VECTOR_STORE_DIR,
        help="Directory to save persistent index",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=128,
        help="Batch size for embedding generation",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force rebuild even if index already exists",
    )
    args = parser.parse_args()

    train_path = os.path.abspath(args.train_data)
    out_dir = os.path.abspath(args.output_dir)

    print("=== PHASE 3: BUILDING PERSISTENT RAG VECTOR INDEX ===")
    print(f"Reference Dataset: {train_path}")
    print(f"Index Directory:   {out_dir}")
    print(f"Force Rebuild:     {args.force}")

    if not os.path.exists(train_path):
        print(f"Error: Reference dataset not found at '{train_path}'. Run prepare_dataset.py first.")
        sys.exit(1)

    builder = VectorIndexBuilder(vector_store_dir=out_dir)
    stats = builder.build_index(
        train_data_path=train_path,
        force_rebuild=args.force,
        batch_size=args.batch_size,
    )

    print("\n=== VECTOR INDEX SUMMARY ===")
    print(f"Status:             {stats.get('status')}")
    print(f"Indexed Records:    {stats.get('indexed_records')}")
    print(f"Embedding Dim:      {stats.get('embedding_dimension')}")
    print(f"Scam Records:       {stats.get('scam_records')}")
    print(f"Legit Records:      {stats.get('legit_records')}")
    if "embedding_time_seconds" in stats:
        print(f"Embedding Time:     {stats['embedding_time_seconds']}s")
        print(f"Total Time:         {stats['total_time_seconds']}s")
    if stats.get("chroma_populated"):
        print(f"ChromaDB Collection: Populated ({stats.get('chroma_records')} items)")
    print(f"Index Path:         {stats.get('numpy_index_path')}")


if __name__ == "__main__":
    main()
