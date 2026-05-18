"""Dense retriever: embed a query, search the FAISS store.

Thin orchestration layer — the embedder and vector store do the real work.
The retriever exists as its own object so the query router can swap in
different embedders or point at different stores without touching the rest
of the pipeline.
"""

from __future__ import annotations

import logging
from typing import Any

from app.embeddings.base import EmbeddingModel
from app.retrieval.vector_store import FaissStore

logger = logging.getLogger(__name__)


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

    @property
    def embedder(self) -> EmbeddingModel:
        return self._embedder

    @property
    def store(self) -> FaissStore:
        return self._store

    def retrieve(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Retrieve top-``k`` hits for a single query string."""
        if k < 1:
            raise ValueError(f"k must be >= 1, got {k}")
        if not query or not query.strip():
            return []

        # encode_queries may add model-specific prefixes (E5 does).
        q_vec = self._embedder.encode_queries([query])
        # encode_queries returns (1, dim); pass the 1-D vector to search.
        return self._store.search(q_vec[0], k=k)
