from functools import lru_cache
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    # NOTE: cold start can be heavy; caching helps for warm invocations.
    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def embed_texts(texts: List[str]) -> np.ndarray:
    """
    Returns float32 matrix of shape (n, d), L2-normalized.
    """
    if not texts:
        return np.zeros((0, 384), dtype=np.float32)
    emb = _model().encode(texts, normalize_embeddings=True)
    return np.asarray(emb, dtype=np.float32)
