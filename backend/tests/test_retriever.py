"""Tests for :class:`app.retrieval.retriever.DenseRetriever`.

Uses the same :class:`DummyEmbedder` pattern as ``test_embeddings.py``
and a real :class:`FaissStore` with toy 8-dim vectors.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.embeddings.base import EmbeddingModel
from app.retrieval.retriever import DenseRetriever
from app.retrieval.vector_store import FaissStore


class _DummyEmbedder(EmbeddingModel):
    """Deterministic hash-based embedder. Same as test_embeddings.py."""

    name = "dummy"

    def __init__(self, dim: int = 8) -> None:
        self._dim = dim
        self.last_query_call: list[str] | None = None

    @property
    def dim(self) -> int:
        return self._dim

    def _hash_encode(self, texts):
        if not texts:
            return np.zeros((0, self._dim), dtype=np.float32)
        vecs = np.stack(
            [
                np.random.default_rng(seed=hash(t) % (2**32))
                .standard_normal(self._dim)
                .astype(np.float32)
                for t in texts
            ]
        )
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vecs / norms

    def encode(self, texts, *, batch_size=32, show_progress=False):
        return self._hash_encode(texts)

    def encode_queries(self, queries, *, batch_size=32, show_progress=False):
        # Record that query-side encoding was used (not generic encode).
        self.last_query_call = list(queries)
        return self._hash_encode(queries)


@pytest.fixture
def populated_store():
    """A store holding 5 deterministically-encoded documents."""
    store = FaissStore(dim=8)
    embedder = _DummyEmbedder(dim=8)
    texts = ["apple", "banana", "cherry", "date", "elderberry"]
    vecs = embedder.encode(texts)
    store.add(
        vecs,
        metadatas=[{"text": t, "source": "fruits"} for t in texts],
    )
    return embedder, store


class TestBasicRetrieve:
    def test_retrieves_self_as_top_hit(self, populated_store):
        embedder, store = populated_store
        retriever = DenseRetriever(embedder, store)
        results = retriever.retrieve("banana", k=3)
        assert len(results) == 3
        assert results[0]["text"] == "banana"
        assert results[0]["score"] == pytest.approx(1.0, abs=1e-5)

    def test_uses_encode_queries_not_encode(self, populated_store):
        """Retriever must call encode_queries so E5-style prefixes apply."""
        embedder, store = populated_store
        retriever = DenseRetriever(embedder, store)
        retriever.retrieve("cherry", k=1)
        assert embedder.last_query_call == ["cherry"]

    def test_k_larger_than_store(self, populated_store):
        embedder, store = populated_store
        retriever = DenseRetriever(embedder, store)
        results = retriever.retrieve("apple", k=100)
        assert len(results) == 5  # cap at store size

    def test_empty_query_returns_empty(self, populated_store):
        embedder, store = populated_store
        retriever = DenseRetriever(embedder, store)
        assert retriever.retrieve("", k=5) == []
        assert retriever.retrieve("   ", k=5) == []

    def test_k_zero_raises(self, populated_store):
        embedder, store = populated_store
        retriever = DenseRetriever(embedder, store)
        with pytest.raises(ValueError, match="k"):
            retriever.retrieve("apple", k=0)


class TestConstruction:
    def test_dim_mismatch_raises(self):
        embedder = _DummyEmbedder(dim=8)
        store = FaissStore(dim=16)
        with pytest.raises(ValueError, match="dim"):
            DenseRetriever(embedder, store)

    def test_exposes_embedder_and_store(self, populated_store):
        embedder, store = populated_store
        retriever = DenseRetriever(embedder, store)
        assert retriever.embedder is embedder
        assert retriever.store is store


class TestEmptyStore:
    def test_empty_store_returns_empty(self):
        embedder = _DummyEmbedder(dim=8)
        store = FaissStore(dim=8)
        retriever = DenseRetriever(embedder, store)
        assert retriever.retrieve("anything", k=5) == []
