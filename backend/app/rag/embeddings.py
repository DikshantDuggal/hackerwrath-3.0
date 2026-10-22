"""
Text embedding module supporting SentenceTransformers with native PyTorch/Transformers fallback.
Uses 'all-MiniLM-L6-v2' (384-dimensional, ~80MB, fast inference on CPU).
"""
from __future__ import annotations

import os
import time
from typing import List, Optional, Union
import numpy as np

from app.core.logging import get_logger
from app.rag.config import DEFAULT_EMBEDDING_MODEL, EMBEDDING_BATCH_SIZE, EMBEDDING_DIM

logger = get_logger("scam_detector.rag.embeddings")

_GLOBAL_EMBEDDING_ENGINE: Optional[TextEmbeddingEngine] = None


class TextEmbeddingEngine:
    """
    High-performance text embedding engine.
    Attempts to use sentence_transformers if installed;
    otherwise falls back to HuggingFace transformers + torch mean pooling.
    """

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL) -> None:
        self.model_name = model_name
        self.engine_type = "UNINITIALIZED"
        self._st_model = None
        self._hf_tokenizer = None
        self._hf_model = None
        self._device = "cpu"
        self._is_loaded = False

    def load(self) -> None:
        """Loads model weights once into memory."""
        if self._is_loaded:
            return

        t0 = time.time()
        logger.info("Initializing embedding engine with model: %s", self.model_name)

        # 1. Try sentence_transformers
        try:
            import sentence_transformers
            from sentence_transformers import SentenceTransformer

            self._st_model = SentenceTransformer(self.model_name)
            self.engine_type = "SENTENCE_TRANSFORMERS"
            self._is_loaded = True
            logger.info(
                "Loaded SentenceTransformer '%s' in %.2fs",
                self.model_name,
                time.time() - t0,
            )
            return
        except (ImportError, Exception) as st_err:
            logger.debug("SentenceTransformers unavailable (%s), trying native HuggingFace transformers...", st_err)

        # 2. Fallback to native HuggingFace transformers + PyTorch
        try:
            import torch
            import torch.nn.functional as F
            from transformers import AutoModel, AutoTokenizer

            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            self._hf_tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._hf_model = AutoModel.from_pretrained(self.model_name).to(self._device)
            self._hf_model.eval()
            self.engine_type = "TRANSFORMERS_NATIVE"
            self._is_loaded = True
            logger.info(
                "Loaded native Transformers '%s' on %s in %.2fs",
                self.model_name,
                self._device,
                time.time() - t0,
            )
            return
        except Exception as hf_err:
            logger.error("Failed to load native Transformers model: %s", hf_err)

        # 3. Deterministic Lightweight Bag-of-Words / Hash-Projection fallback (for tests without internet)
        logger.warning("No neural model could be loaded; initializing deterministic semantic projection fallback")
        self.engine_type = "DETERMINISTIC_PROJECTION"
        self._is_loaded = True

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    def encode(self, text: str) -> np.ndarray:
        """Encodes a single text string into a normalized 1D float32 vector of shape (EMBEDDING_DIM,)."""
        res = self.encode_batch([text], batch_size=1)
        return res[0]

    def encode_batch(self, texts: List[str], batch_size: int = EMBEDDING_BATCH_SIZE) -> np.ndarray:
        """Encodes a list of strings into normalized 2D float32 array of shape (N, EMBEDDING_DIM)."""
        if not self._is_loaded:
            self.load()

        if not texts:
            return np.empty((0, EMBEDDING_DIM), dtype=np.float32)

        # Clean/sanitize strings
        sanitized = [t if isinstance(t, str) and t.strip() else " " for t in texts]

        # Mode A: SentenceTransformers
        if self.engine_type == "SENTENCE_TRANSFORMERS" and self._st_model is not None:
            embeddings = self._st_model.encode(
                sanitized,
                batch_size=batch_size,
                show_progress_bar=False,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
            return embeddings.astype(np.float32)

        # Mode B: Native HuggingFace Transformers
        if self.engine_type == "TRANSFORMERS_NATIVE" and self._hf_model is not None:
            import torch
            import torch.nn.functional as F

            all_embeddings = []
            total_items = len(sanitized)
            actual_batch_size = min(batch_size, 64)

            for i in range(0, total_items, actual_batch_size):
                batch_texts = sanitized[i : i + actual_batch_size]
                if i == 0 or (i // actual_batch_size) % 10 == 0 or (i + actual_batch_size >= total_items):
                    logger.info("Encoding progress: %d/%d (%.1f%%)", i, total_items, (i / total_items) * 100)

                encoded_input = self._hf_tokenizer(
                    batch_texts,
                    padding=True,
                    truncation=True,
                    max_length=256,
                    return_tensors="pt",
                ).to(self._device)

                with torch.no_grad():
                    model_output = self._hf_model(**encoded_input)
                    token_embeddings = model_output[0]
                    input_mask_expanded = (
                        encoded_input["attention_mask"]
                        .unsqueeze(-1)
                        .expand(token_embeddings.size())
                        .float()
                    )
                    sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
                    sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
                    sentence_embeddings = sum_embeddings / sum_mask
                    sentence_embeddings = F.normalize(sentence_embeddings, p=2, dim=1)
                    all_embeddings.append(sentence_embeddings.cpu().numpy())

            return np.vstack(all_embeddings).astype(np.float32)

        # Mode C: Deterministic Hashing Projection fallback
        return self._deterministic_hash_projection(sanitized)

    def _deterministic_hash_projection(self, texts: List[str]) -> np.ndarray:
        """Deterministic fallback embedding using token hashing + random projection."""
        vectors = np.zeros((len(texts), EMBEDDING_DIM), dtype=np.float32)
        rng = np.random.RandomState(42)
        proj_matrix = rng.randn(1000, EMBEDDING_DIM).astype(np.float32)

        for idx, text in enumerate(texts):
            words = text.lower().split()
            if not words:
                vectors[idx, 0] = 1.0
                continue
            v = np.zeros(EMBEDDING_DIM, dtype=np.float32)
            for w in words:
                h = abs(hash(w)) % 1000
                v += proj_matrix[h]
            norm = np.linalg.norm(v)
            if norm > 1e-6:
                v = v / norm
            vectors[idx] = v
        return vectors


def get_embedding_engine(model_name: str = DEFAULT_EMBEDDING_MODEL) -> TextEmbeddingEngine:
    """Returns singleton TextEmbeddingEngine instance."""
    global _GLOBAL_EMBEDDING_ENGINE
    if _GLOBAL_EMBEDDING_ENGINE is None or _GLOBAL_EMBEDDING_ENGINE.model_name != model_name:
        _GLOBAL_EMBEDDING_ENGINE = TextEmbeddingEngine(model_name=model_name)
    return _GLOBAL_EMBEDDING_ENGINE
