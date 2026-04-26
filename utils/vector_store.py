from typing import List, Tuple

import faiss
import numpy as np


class InMemoryFAISS:
    """
    Tiny in-memory vector store for serverless usage (per-request).
    Uses inner product on normalized embeddings (cosine similarity).
    """

    def __init__(self, embeddings: np.ndarray, texts: List[str]):
        if embeddings.dtype != np.float32:
            embeddings = embeddings.astype(np.float32)
        self.texts = texts
        self.dim = int(embeddings.shape[1]) if embeddings.size else 384
        self.index = faiss.IndexFlatIP(self.dim)
        if embeddings.size:
            self.index.add(embeddings)

    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Tuple[float, str]]:
        if self.index.ntotal == 0:
            return []
        q = query_embedding.astype(np.float32)
        if q.ndim == 1:
            q = q.reshape(1, -1)
        scores, idxs = self.index.search(q, k)
        out: List[Tuple[float, str]] = []
        for score, idx in zip(scores[0].tolist(), idxs[0].tolist()):
            if idx == -1:
                continue
            out.append((float(score), self.texts[idx]))
        return out
