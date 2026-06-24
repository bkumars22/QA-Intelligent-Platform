"""Sentence-transformer embedder — lazy-loaded, normalised, 384-dim.

Model: all-MiniLM-L6-v2  (free, runs locally, ~90 MB)
Output: L2-normalised float32 list — cosine similarity = dot product.
Falls back to a deterministic hash-based vector when the model cannot
be loaded (CI environments, cold Railway containers).
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Sequence

import numpy as np

logger = logging.getLogger("rag.embedder")

_EMBED_DIM = 384
_MODEL_NAME = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")
_model = None


def _load_model():
    global _model
    if _model is not None:
        return _model
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(_MODEL_NAME)
        logger.info("Loaded embedding model %s", _MODEL_NAME)
    except Exception as exc:
        logger.warning("sentence-transformers unavailable (%s) — using hash fallback", exc)
        _model = None
    return _model


def _hash_embed(text: str) -> list[float]:
    """Deterministic 384-dim pseudo-embedding from SHA-256 — used as fallback."""
    seed = int(hashlib.sha256(text.encode()).hexdigest(), 16) % (2**31)
    rng = np.random.default_rng(seed)
    vec = rng.standard_normal(_EMBED_DIM).astype(np.float32)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec.tolist()


def embed(text: str) -> list[float]:
    """Embed a single string. Returns a normalised 384-dim float list."""
    text = text.strip()
    if not text:
        return [0.0] * _EMBED_DIM

    model = _load_model()
    if model is None:
        return _hash_embed(text)

    try:
        vec = model.encode(text, normalize_embeddings=True, show_progress_bar=False)
        return vec.tolist()
    except Exception as exc:
        logger.warning("Embedding failed (%s) — using hash fallback", exc)
        return _hash_embed(text)


def embed_batch(texts: Sequence[str]) -> list[list[float]]:
    """Embed multiple texts. More efficient than calling embed() in a loop."""
    if not texts:
        return []

    model = _load_model()
    if model is None:
        return [_hash_embed(t) for t in texts]

    try:
        vecs = model.encode(
            list(texts),
            normalize_embeddings=True,
            batch_size=32,
            show_progress_bar=False,
        )
        return vecs.tolist()
    except Exception as exc:
        logger.warning("Batch embedding failed (%s) — using hash fallback", exc)
        return [_hash_embed(t) for t in texts]
