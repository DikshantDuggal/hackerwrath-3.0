"""
Configuration settings for RAG Retrieval & Classification Module.
"""
from __future__ import annotations

import os
from typing import Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Embedding configuration
DEFAULT_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
EMBEDDING_DIM = int(os.getenv("RAG_EMBEDDING_DIM", "384"))
EMBEDDING_BATCH_SIZE = int(os.getenv("RAG_BATCH_SIZE", "64"))

# Vector Store configuration
VECTOR_STORE_DIR = os.getenv("RAG_VECTOR_STORE_DIR", os.path.join(BASE_DIR, "vector_store"))
CHROMA_PERSIST_DIR = os.path.join(VECTOR_STORE_DIR, "chroma")
CHROMA_COLLECTION_NAME = os.getenv("RAG_CHROMA_COLLECTION", "scam_detection_corpus")
NUMPY_INDEX_PATH = os.path.join(VECTOR_STORE_DIR, "index_embeddings.npz")
METADATA_INDEX_PATH = os.path.join(VECTOR_STORE_DIR, "index_metadata.jsonl")

# Dataset Paths
DATA_DIR = os.getenv("RAG_DATA_DIR", os.path.join(BASE_DIR, "data"))
TRAIN_DATA_PATH = os.path.join(DATA_DIR, "train.jsonl")
VAL_DATA_PATH = os.path.join(DATA_DIR, "val.jsonl")
TEST_DATA_PATH = os.path.join(DATA_DIR, "test.jsonl")

# Retrieval & Classification Parameters
DEFAULT_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
WEAK_EVIDENCE_SIMILARITY_THRESHOLD = float(os.getenv("RAG_SIM_THRESHOLD", "0.38"))
STRONG_EVIDENCE_SIMILARITY_THRESHOLD = float(os.getenv("RAG_STRONG_SIM_THRESHOLD", "0.68"))
AMBIGUITY_MARGIN = float(os.getenv("RAG_AMBIGUITY_MARGIN", "0.10"))

# Baseline Model Paths
BASELINE_MODEL_PATH = os.path.join(VECTOR_STORE_DIR, "tfidf_logistic_baseline.joblib")
