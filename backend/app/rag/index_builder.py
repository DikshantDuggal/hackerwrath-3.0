"""
Persistent vector index builder for RAG scam detection.
Builds both ChromaDB collection and ultra-fast NumPy persistent index.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from app.core.logging import get_logger
from app.rag.config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_PERSIST_DIR,
    METADATA_INDEX_PATH,
    NUMPY_INDEX_PATH,
    TRAIN_DATA_PATH,
    VECTOR_STORE_DIR,
)
from app.rag.embeddings import get_embedding_engine

logger = get_logger("scam_detector.rag.index_builder")


class VectorIndexBuilder:
    """
    Manages vector index construction, batch encoding, and persistence.
    """

    def __init__(self, vector_store_dir: str = VECTOR_STORE_DIR) -> None:
        self.vector_store_dir = vector_store_dir
        os.makedirs(self.vector_store_dir, exist_ok=True)
        self.embedding_engine = get_embedding_engine()

    def build_index(
        self,
        train_data_path: str = TRAIN_DATA_PATH,
        force_rebuild: bool = False,
        batch_size: int = 128,
    ) -> Dict[str, Any]:
        """
        Builds persistent vector index from reference training data.
        Avoids redundant rebuilding when index already exists unless force_rebuild=True.
        """
        t0 = time.time()
        numpy_exists = os.path.exists(NUMPY_INDEX_PATH) and os.path.exists(METADATA_INDEX_PATH)

        if numpy_exists and not force_rebuild:
            logger.info("Persistent vector index already exists at '%s'. Skipping build.", NUMPY_INDEX_PATH)
            stats = self.get_index_stats()
            stats["status"] = "ALREADY_EXISTS"
            return stats

        if not os.path.exists(train_data_path):
            raise FileNotFoundError(f"Training dataset not found at '{train_data_path}'")

        # 1. Load reference records
        records: List[Dict[str, Any]] = []
        with open(train_data_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))

        total_records = len(records)
        logger.info("Loaded %d training records for vector index construction.", total_records)

        # 2. Extract texts and metadata
        texts = [r["text"] for r in records]
        example_ids = [r["example_id"] for r in records]
        labels = [r["label"] for r in records]

        # 3. Batch Embedding
        t_embed_start = time.time()
        logger.info("Generating embeddings using '%s' in batches of %d...", self.embedding_engine.model_name, batch_size)
        embeddings = self.embedding_engine.encode_batch(texts, batch_size=batch_size)
        embed_time = time.time() - t_embed_start
        logger.info("Generated %d embeddings in %.2fs (shape: %s)", len(embeddings), embed_time, embeddings.shape)

        # 4. Save persistent NumPy Index
        np.savez_compressed(
            NUMPY_INDEX_PATH,
            embeddings=embeddings,
            example_ids=np.array(example_ids),
            labels=np.array(labels),
        )

        with open(METADATA_INDEX_PATH, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

        # 5. Populate ChromaDB if available
        chroma_populated = False
        chroma_count = 0
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
            client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

            # Recreate collection cleanly if force_rebuild
            if force_rebuild:
                try:
                    client.delete_collection(CHROMA_COLLECTION_NAME)
                except Exception:
                    pass

            collection = client.get_or_create_collection(
                name=CHROMA_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )

            # Insert in chunks of 500 to Chroma
            chunk_size = 500
            for i in range(0, total_records, chunk_size):
                chunk_ids = example_ids[i : i + chunk_size]
                chunk_embs = embeddings[i : i + chunk_size].tolist()
                chunk_docs = texts[i : i + chunk_size]
                chunk_metas = [
                    {
                        "label": labels[j],
                        "source": records[j].get("source", "TeleAntiFraud-28k"),
                        "word_count": records[j].get("word_count", 0),
                    }
                    for j in range(i, min(i + chunk_size, total_records))
                ]
                collection.upsert(
                    ids=chunk_ids,
                    embeddings=chunk_embs,
                    documents=chunk_docs,
                    metadatas=chunk_metas,
                )

            chroma_count = collection.count()
            chroma_populated = True
            logger.info("Successfully populated ChromaDB collection '%s' with %d records.", CHROMA_COLLECTION_NAME, chroma_count)
        except Exception as chroma_err:
            logger.info("ChromaDB indexing skipped or deferred (%s); NumPy high-speed vector index active.", chroma_err)

        total_time = time.time() - t0
        stats = {
            "status": "BUILT",
            "indexed_records": total_records,
            "embedding_dimension": int(embeddings.shape[1]),
            "scam_records": sum(1 for l in labels if l == "SCAM"),
            "legit_records": sum(1 for l in labels if l == "LEGITIMATE"),
            "embedding_time_seconds": round(embed_time, 2),
            "total_time_seconds": round(total_time, 2),
            "numpy_index_path": NUMPY_INDEX_PATH,
            "chroma_populated": chroma_populated,
            "chroma_records": chroma_count,
        }
        return stats

    def get_index_stats(self) -> Dict[str, Any]:
        """Returns statistics on current index state."""
        if not os.path.exists(NUMPY_INDEX_PATH):
            return {
                "status": "NOT_FOUND",
                "indexed_records": 0,
                "dimension": 0,
            }

        try:
            data = np.load(NUMPY_INDEX_PATH)
            embs = data["embeddings"]
            labels = data["labels"]
            file_size_mb = os.path.getsize(NUMPY_INDEX_PATH) / (1024 * 1024)
            return {
                "status": "READY",
                "indexed_records": int(embs.shape[0]),
                "dimension": int(embs.shape[1]),
                "scam_records": int(np.sum(labels == "SCAM")),
                "legit_records": int(np.sum(labels == "LEGITIMATE")),
                "index_file_size_mb": round(file_size_mb, 2),
            }
        except Exception as e:
            return {"status": "ERROR", "error": str(e), "indexed_records": 0}
