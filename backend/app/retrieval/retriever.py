"""Dense retriever: embed a query, search the FAISS store.

Thin orchestration layer — the embedder and vector store do the real work.
The retriever exists as its own object so the query router can swap in
different embedders or point at different stores without touching the rest
of the pipeline.
"""

from __future__ import annotations

import hashlib
import logging
from collections import OrderedDict
from typing import Any

import numpy as np

from app.embeddings.base import EmbeddingModel
from app.retrieval.vector_store import FaissStore

logger = logging.getLogger(__name__)

_CACHE_MAX = 128


class _EmbeddingCache:
    """LRU cache for query embeddings to avoid re-encoding repeated queries."""

    def __init__(self, maxsize: int = _CACHE_MAX) -> None:
        self._cache: OrderedDict[str, np.ndarray] = OrderedDict()
        self._maxsize = maxsize

    def get(self, key: str) -> np.ndarray | None:
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def put(self, key: str, value: np.ndarray) -> None:
        self._cache[key] = value
        self._cache.move_to_end(key)
        if len(self._cache) > self._maxsize:
            self._cache.popitem(last=False)


class DenseRetriever:
    """Embeds a query via :class:`EmbeddingModel.encode_queries`, then searches.

    Parameters
    ----------
    embedder:
        The embedder used for queries. Must match the model that produced
        the vectors stored in ``store`` — there is no sanity check here beyond
        dimension alignment, so mixing embedders will silently return garbage.
    store:
        A populated :class:`FaissStore`.
    """

    def __init__(self, embedder: EmbeddingModel, store: FaissStore) -> None:
        if embedder.dim != store.dim:
            raise ValueError(
                f"Embedder dim {embedder.dim} != store dim {store.dim}; they must match"
            )
        self._embedder = embedder
        self._store = store
        self._cache = _EmbeddingCache()

    @property
    def embedder(self) -> EmbeddingModel:
        return self._embedder

    @property
    def store(self) -> FaissStore:
        return self._store

    def _encode_cached(self, query: str) -> np.ndarray:
        key = hashlib.sha256(query.encode()).hexdigest()
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        q_vec = self._embedder.encode_queries([query])[0]
        self._cache.put(key, q_vec)
        return q_vec

    def retrieve(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Retrieve top-``k`` hits for a single query string."""
        if k < 1:
            raise ValueError(f"k must be >= 1, got {k}")
        if not query or not query.strip():
            return []

        q_vec = self._encode_cached(query)
        return self._store.search(q_vec, k=k)
