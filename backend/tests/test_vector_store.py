"""Tests for :class:`app.retrieval.vector_store.FaissStore`.

All tests use toy random vectors (8-dim or 16-dim) — no real embedding model
is loaded. Covers both ``flat`` and ``ivfpq`` index types, add/search/delete/
save/load, metadata round-tripping, and input validation.
"""

from __future__ import annotations

import sys

import numpy as np
import pytest

from app.retrieval.vector_store import FaissStore


# ---------------------------------------------------------------------- #
# Helpers
# ---------------------------------------------------------------------- #


def _rand_normalized(n: int, dim: int, seed: int = 0) -> np.ndarray:
    """Return ``(n, dim)`` L2-normalized random float32 vectors."""
    rng = np.random.default_rng(seed)
    vecs = rng.standard_normal((n, dim)).astype(np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vecs / norms


# ---------------------------------------------------------------------- #
# Construction & validation
# ---------------------------------------------------------------------- #


class TestConstruction:
    def test_flat_default_construction(self):
        store = FaissStore(dim=8)
        assert store.dim == 8
        assert store.index_type == "flat"
        assert len(store) == 0
        assert store.is_trained  # flat index is trained from the start

    def test_ivfpq_construction(self):
        store = FaissStore(dim=16, index_type="ivfpq", ivfpq_nlist=4, ivfpq_m=4)
        assert store.index_type == "ivfpq"
        assert store.dim == 16
        assert len(store) == 0
        # IVF-PQ needs training data; fresh index is not trained yet.
        assert not store.is_trained

    def test_invalid_dim_raises(self):
        with pytest.raises(ValueError, match="dim"):
            FaissStore(dim=0)

    def test_invalid_index_type_raises(self):
        with pytest.raises(ValueError, match="index_type"):
            FaissStore(dim=8, index_type="hnsw")  # type: ignore[arg-type]

    def test_ivfpq_m_must_divide_dim(self):
        with pytest.raises(ValueError, match="divide"):
            FaissStore(dim=10, index_type="ivfpq", ivfpq_m=4)


# ---------------------------------------------------------------------- #
# Flat index: add / search
# ---------------------------------------------------------------------- #


class TestFlatAddSearch:
    def test_add_returns_sequential_ids(self):
        store = FaissStore(dim=8)
        vecs = _rand_normalized(3, 8)
        ids = store.add(vecs)
        assert ids == [1, 2, 3]
        assert len(store) == 3

    def test_add_multiple_batches_continues_ids(self):
        store = FaissStore(dim=8)
        store.add(_rand_normalized(3, 8, seed=1))
        ids2 = store.add(_rand_normalized(2, 8, seed=2))
        assert ids2 == [4, 5]
        assert len(store) == 5

    def test_add_empty_returns_empty_list(self):
        store = FaissStore(dim=8)
        ids = store.add(np.zeros((0, 8), dtype=np.float32))
        assert ids == []
        assert len(store) == 0

    def test_add_wrong_dim_raises(self):
        store = FaissStore(dim=8)
        with pytest.raises(ValueError, match="dim"):
            store.add(_rand_normalized(2, 16))

    def test_add_wrong_ndim_raises(self):
        store = FaissStore(dim=8)
        with pytest.raises(ValueError, match="shape"):
            store.add(np.zeros((8,), dtype=np.float32))

    def test_add_metadata_length_mismatch_raises(self):
        store = FaissStore(dim=8)
        with pytest.raises(ValueError, match="length"):
            store.add(_rand_normalized(3, 8), metadatas=[{"text": "a"}])

    def test_search_returns_self_as_top_hit(self):
        """A vector identical to one in the index must be its own top match."""
        store = FaissStore(dim=8)
        vecs = _rand_normalized(5, 8)
        ids = store.add(
            vecs, metadatas=[{"text": f"doc{i}", "source": "test"} for i in range(5)]
        )
        # Query with the 3rd vector (id=3)
        results = store.search(vecs[2], k=3)
        assert len(results) == 3
        assert results[0]["id"] == ids[2]
        assert results[0]["text"] == "doc2"
        assert results[0]["score"] == pytest.approx(1.0, abs=1e-5)

    def test_search_ordered_by_score_desc(self):
        store = FaissStore(dim=8)
        vecs = _rand_normalized(10, 8, seed=42)
        store.add(vecs)
        q = _rand_normalized(1, 8, seed=99)[0]
        results = store.search(q, k=5)
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_search_accepts_1d_and_2d_query(self):
        store = FaissStore(dim=8)
        vecs = _rand_normalized(4, 8)
        store.add(vecs)
        r1 = store.search(vecs[0], k=2)
        r2 = store.search(vecs[0:1], k=2)
        assert [h["id"] for h in r1] == [h["id"] for h in r2]

    def test_search_empty_index_returns_empty(self):
        store = FaissStore(dim=8)
        q = _rand_normalized(1, 8)[0]
        assert store.search(q, k=5) == []

    def test_search_k_larger_than_ntotal(self):
        store = FaissStore(dim=8)
        store.add(_rand_normalized(3, 8))
        results = store.search(_rand_normalized(1, 8)[0], k=10)
        # FAISS returns -1 for unused slots; our wrapper filters them.
        assert len(results) == 3

    def test_search_wrong_dim_raises(self):
        store = FaissStore(dim=8)
        store.add(_rand_normalized(1, 8))
        with pytest.raises(ValueError, match="dim"):
            store.search(_rand_normalized(1, 16)[0], k=1)

    def test_search_invalid_k_raises(self):
        store = FaissStore(dim=8)
        store.add(_rand_normalized(1, 8))
        with pytest.raises(ValueError, match="k"):
            store.search(_rand_normalized(1, 8)[0], k=0)


# ---------------------------------------------------------------------- #
# Metadata handling
# ---------------------------------------------------------------------- #


class TestMetadata:
    def test_recognized_fields_stored_as_columns(self):
        store = FaissStore(dim=8)
        store.add(
            _rand_normalized(2, 8),
            metadatas=[
                {"text": "hello", "source": "a.txt", "language": "en"},
                {"text": "नमस्ते", "source": "b.txt", "language": "hi"},
            ],
        )
        results = store.search(_rand_normalized(1, 8, seed=7)[0], k=2)
        langs = {r["language"] for r in results}
        assert langs == {"en", "hi"}

    def test_extra_fields_roundtrip_via_json(self):
        store = FaissStore(dim=8)
        vecs = _rand_normalized(1, 8)
        store.add(
            vecs,
            metadatas=[
                {
                    "text": "t",
                    "source": "s",
                    "language": "en",
                    "chunk_index": 7,
                    "extra_list": [1, 2, 3],
                    "nested": {"k": "v"},
                }
            ],
        )
        [hit] = store.search(vecs[0], k=1)
        assert hit["chunk_index"] == 7
        assert hit["extra_list"] == [1, 2, 3]
        assert hit["nested"] == {"k": "v"}

    def test_missing_metadata_fields_get_defaults(self):
        store = FaissStore(dim=8)
        vecs = _rand_normalized(1, 8)
        store.add(vecs, metadatas=[{}])
        [hit] = store.search(vecs[0], k=1)
        assert hit["text"] == ""
        assert hit["source"] == ""
        assert hit["language"] == "unknown"

    def test_unicode_preserved_in_metadata(self):
        store = FaissStore(dim=8)
        vecs = _rand_normalized(1, 8)
        store.add(
            vecs,
            metadatas=[{"text": "भारत एक देश है।", "source": "wiki/भारत", "language": "hi"}],
        )
        [hit] = store.search(vecs[0], k=1)
        assert hit["text"] == "भारत एक देश है।"
        assert hit["source"] == "wiki/भारत"


# ---------------------------------------------------------------------- #
# Delete
# ---------------------------------------------------------------------- #


class TestDelete:
    def test_delete_removes_metadata(self):
        store = FaissStore(dim=8)
        vecs = _rand_normalized(5, 8)
        ids = store.add(vecs, metadatas=[{"text": f"d{i}"} for i in range(5)])
        n_removed = store.delete([ids[1], ids[3]])
        assert n_removed == 2
        # Plain IndexFlatIP can't remove vectors, so ntotal stays at 5.
        # But search should only return 3 results (deleted metadata is skipped).
        results = store.search(vecs[0], k=10)
        assert len(results) == 3

    def test_deleted_ids_absent_from_search(self):
        store = FaissStore(dim=8)
        vecs = _rand_normalized(5, 8)
        ids = store.add(vecs, metadatas=[{"text": f"d{i}"} for i in range(5)])
        store.delete([ids[0]])
        # Query identical to deleted vec[0] — it should not appear.
        results = store.search(vecs[0], k=5)
        result_ids = {r["id"] for r in results}
        assert ids[0] not in result_ids
        assert len(results) == 4

    def test_delete_empty_list_is_noop(self):
        store = FaissStore(dim=8)
        store.add(_rand_normalized(3, 8))
        assert store.delete([]) == 0
        assert len(store) == 3

    def test_delete_nonexistent_id_returns_zero(self):
        store = FaissStore(dim=8)
        store.add(_rand_normalized(2, 8))
        n = store.delete([999])
        assert n == 0


# ---------------------------------------------------------------------- #
# Stats
# ---------------------------------------------------------------------- #


class TestStats:
    def test_stats_structure(self):
        store = FaissStore(dim=8)
        store.add(
            _rand_normalized(3, 8),
            metadatas=[
                {"language": "en"},
                {"language": "hi"},
                {"language": "hi"},
            ],
        )
        s = store.stats()
        assert s["index_type"] == "flat"
        assert s["dim"] == 8
        assert s["ntotal"] == 3
        assert s["is_trained"] is True
        assert s["by_language"] == {"en": 1, "hi": 2}
        assert s["next_id"] == 4


# ---------------------------------------------------------------------- #
# Save / load round-trip
# ---------------------------------------------------------------------- #


class TestSaveLoad:
    def test_flat_roundtrip_preserves_search_results(self, tmp_path):
        store = FaissStore(dim=8)
        vecs = _rand_normalized(10, 8, seed=7)
        store.add(
            vecs,
            metadatas=[{"text": f"d{i}", "language": "en"} for i in range(10)],
        )
        before = store.search(vecs[3], k=5)

        save_dir = tmp_path / "store"
        store.save(save_dir)

        assert (save_dir / "index.faiss").exists()
        assert (save_dir / "metadata.sqlite").exists()
        assert (save_dir / "config.json").exists()

        loaded = FaissStore.load(save_dir)
        assert len(loaded) == len(store)
        assert loaded.dim == store.dim
        assert loaded.index_type == "flat"

        after = loaded.search(vecs[3], k=5)
        assert [h["id"] for h in before] == [h["id"] for h in after]
        assert [h["text"] for h in before] == [h["text"] for h in after]

    def test_next_id_preserved_after_load(self, tmp_path):
        store = FaissStore(dim=8)
        store.add(_rand_normalized(3, 8))
        store.save(tmp_path / "s")
        loaded = FaissStore.load(tmp_path / "s")
        new_ids = loaded.add(_rand_normalized(1, 8))
        assert new_ids == [4]

    def test_delete_then_save_then_load(self, tmp_path):
        store = FaissStore(dim=8)
        vecs = _rand_normalized(5, 8)
        ids = store.add(vecs, metadatas=[{"text": f"d{i}"} for i in range(5)])
        store.delete([ids[0], ids[1]])
        store.save(tmp_path / "s")
        loaded = FaissStore.load(tmp_path / "s")
        # ntotal stays at 5 (plain IndexFlatIP), but only 3 metadata rows.
        results = loaded.search(vecs[2], k=10)
        assert len(results) == 3


# ---------------------------------------------------------------------- #
# IVF-PQ index
# ---------------------------------------------------------------------- #


@pytest.mark.skipif(
    sys.platform == "darwin",
    reason="IVF-PQ training triggers SIGSEGV on macOS due to torch/faiss OpenMP conflict",
)
class TestIVFPQ:
    """IVF-PQ is approximate; we only check structural invariants and that
    it returns *something* reasonable. Exact score equality is not expected."""

    def test_first_add_triggers_training(self):
        # Use dim=16 with m=4 (16 % 4 == 0), nlist=4 (low, for tiny data).
        store = FaissStore(
            dim=16, index_type="ivfpq", ivfpq_nlist=4, ivfpq_m=4, ivfpq_nbits=4
        )
        assert not store.is_trained
        # Need enough training points — IVF-PQ is picky. Use 256.
        store.add(_rand_normalized(256, 16, seed=1))
        assert store.is_trained
        assert len(store) == 256

    def test_ivfpq_search_returns_results(self):
        store = FaissStore(
            dim=16, index_type="ivfpq", ivfpq_nlist=4, ivfpq_m=4, ivfpq_nbits=4
        )
        vecs = _rand_normalized(256, 16, seed=1)
        store.add(vecs, metadatas=[{"text": f"d{i}"} for i in range(256)])
        results = store.search(vecs[0], k=5)
        assert len(results) == 5
        # Results must be valid dicts with expected keys.
        for r in results:
            assert "id" in r and "score" in r and "text" in r

    def test_ivfpq_roundtrip(self, tmp_path):
        store = FaissStore(
            dim=16, index_type="ivfpq", ivfpq_nlist=4, ivfpq_m=4, ivfpq_nbits=4
        )
        vecs = _rand_normalized(256, 16, seed=3)
        store.add(vecs, metadatas=[{"text": f"d{i}"} for i in range(256)])
        store.save(tmp_path / "ivf")
        loaded = FaissStore.load(tmp_path / "ivf")
        assert loaded.index_type == "ivfpq"
        assert len(loaded) == 256
        # Search returns same number of hits after load.
        assert len(loaded.search(vecs[0], k=5)) == 5
