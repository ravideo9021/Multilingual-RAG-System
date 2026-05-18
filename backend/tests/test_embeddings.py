"""Tests for the embedding subsystem.

These run without downloading any model — all tests use either a ``DummyEmbedder``
subclass or check construction-only behavior of the real wrappers (which defer
model loads until first encode call).

The real BGE-M3 smoke test lives in ``test_bge_m3_smoke.py`` and is gated
behind ``RUN_SLOW_TESTS=1``.
"""

from __future__ import annotations

import json
import os

import numpy as np
import pytest

from app.embeddings.base import EmbeddingModel, resolve_device
from app.embeddings.factory import SUPPORTED_EMBEDDERS, get_embedder


# ---------------------------------------------------------------------- #
# Dummy embedder for testing the ABC
# ---------------------------------------------------------------------- #


class DummyEmbedder(EmbeddingModel):
    """Deterministic fake embedder that hashes texts to vectors."""

    name = "dummy"

    def __init__(self, dim: int = 8) -> None:
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    def encode(self, texts, *, batch_size: int = 32, show_progress: bool = False):
        if not texts:
            return np.zeros((0, self._dim), dtype=np.float32)
        rng = np.random.default_rng(seed=42)
        # Deterministic per-text: hash each text to a seed.
        vecs = np.stack(
            [
                np.random.default_rng(seed=hash(t) % (2**32)).standard_normal(self._dim).astype(
                    np.float32
                )
                for t in texts
            ]
        )
        _ = rng  # keep reference (silences linter about unused)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vecs / norms


# ---------------------------------------------------------------------- #
# resolve_device
# ---------------------------------------------------------------------- #


class TestResolveDevice:
    def test_cpu_always_returns_cpu(self):
        assert resolve_device("cpu") == "cpu"

    def test_auto_returns_valid_string(self):
        d = resolve_device("auto")
        assert d in ("cuda", "mps", "cpu")

    def test_cuda_falls_back_if_unavailable(self):
        # We can't mock torch easily here; just check the return is a known
        # device string.
        d = resolve_device("cuda")
        assert d in ("cuda", "cpu")

    def test_mps_falls_back_if_unavailable(self):
        d = resolve_device("mps")
        assert d in ("mps", "cpu")


# ---------------------------------------------------------------------- #
# EmbeddingModel ABC defaults
# ---------------------------------------------------------------------- #


class TestEmbeddingModelABC:
    def test_encode_queries_defaults_to_encode(self):
        m = DummyEmbedder(dim=8)
        q_vecs = m.encode_queries(["hello"])
        e_vecs = m.encode(["hello"])
        np.testing.assert_array_equal(q_vecs, e_vecs)

    def test_encode_passages_defaults_to_encode(self):
        m = DummyEmbedder(dim=8)
        p_vecs = m.encode_passages(["hello"])
        e_vecs = m.encode(["hello"])
        np.testing.assert_array_equal(p_vecs, e_vecs)

    def test_output_is_l2_normalized(self):
        m = DummyEmbedder(dim=8)
        vecs = m.encode(["apple", "banana", "cherry"])
        norms = np.linalg.norm(vecs, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-5)

    def test_empty_input_returns_empty_array(self):
        m = DummyEmbedder(dim=8)
        vecs = m.encode([])
        assert vecs.shape == (0, 8)
        assert vecs.dtype == np.float32

    def test_deterministic(self):
        m = DummyEmbedder(dim=8)
        a = m.encode(["hello", "world"])
        b = m.encode(["hello", "world"])
        np.testing.assert_array_equal(a, b)

    def test_dim_property(self):
        assert DummyEmbedder(dim=16).dim == 16
        assert DummyEmbedder(dim=1024).dim == 1024


# ---------------------------------------------------------------------- #
# Save/load embeddings cache
# ---------------------------------------------------------------------- #


class TestSaveLoadEmbeddings:
    def test_roundtrip_preserves_values(self, tmp_path):
        m = DummyEmbedder(dim=8)
        vecs = m.encode(["a", "b", "c"])
        meta = [
            {"text": "a", "source": "doc1"},
            {"text": "b", "source": "doc1"},
            {"text": "c", "source": "doc2"},
        ]

        cache = tmp_path / "cache"
        EmbeddingModel.save_embeddings(vecs, meta, cache)

        loaded_vecs, loaded_meta = EmbeddingModel.load_embeddings(cache)
        np.testing.assert_array_equal(vecs, loaded_vecs)
        assert loaded_meta == meta

    def test_roundtrip_preserves_unicode_in_metadata(self, tmp_path):
        m = DummyEmbedder(dim=8)
        vecs = m.encode(["भारत", "India"])
        meta = [
            {"text": "भारत एक देश है।", "language": "hi"},
            {"text": "India is a country.", "language": "en"},
        ]
        cache = tmp_path / "hi_en_cache"
        EmbeddingModel.save_embeddings(vecs, meta, cache)
        _, loaded_meta = EmbeddingModel.load_embeddings(cache)
        assert loaded_meta[0]["text"] == "भारत एक देश है।"
        assert loaded_meta[1]["language"] == "en"

    def test_load_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            EmbeddingModel.load_embeddings(tmp_path / "nonexistent")

    def test_files_created_at_expected_paths(self, tmp_path):
        m = DummyEmbedder(dim=8)
        vecs = m.encode(["x"])
        cache = tmp_path / "sub" / "cache"
        EmbeddingModel.save_embeddings(vecs, [{"text": "x"}], cache)
        assert (tmp_path / "sub" / "cache.npy").exists()
        assert (tmp_path / "sub" / "cache.meta.json").exists()
        # Metadata file is valid JSON with expected structure.
        loaded_meta = json.loads((tmp_path / "sub" / "cache.meta.json").read_text())
        assert loaded_meta == [{"text": "x"}]


# ---------------------------------------------------------------------- #
# Factory dispatch
# ---------------------------------------------------------------------- #


class TestFactory:
    def test_unknown_name_raises(self):
        with pytest.raises(ValueError, match="Unknown embedder"):
            get_embedder("nonexistent-model")

    def test_supported_embedders_listed(self):
        assert set(SUPPORTED_EMBEDDERS) == {"bge-m3", "e5", "openai"}

    def test_bge_m3_constructs_without_loading(self):
        """Constructor must not download the 2.3 GB model."""
        try:
            embedder = get_embedder("bge-m3", device="cpu")
        except ImportError:
            pytest.skip("FlagEmbedding not installed in this environment")
        assert embedder.name == "bge-m3"
        assert embedder.dim == 1024
        # The underlying model slot is still None — no download happened.
        assert embedder._model is None  # type: ignore[attr-defined]

    def test_e5_constructs_without_loading(self):
        try:
            embedder = get_embedder("e5", device="cpu")
        except ImportError:
            pytest.skip("sentence-transformers not installed in this environment")
        assert embedder.name == "e5"
        assert embedder.dim == 1024
        assert embedder._model is None  # type: ignore[attr-defined]

    def test_openai_requires_api_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(ValueError, match="api_key"):
            get_embedder("openai")

    def test_openai_accepts_explicit_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        embedder = get_embedder("openai", api_key="sk-test-fake")
        assert embedder.name == "openai"
        assert embedder.dim == 3072

    def test_openai_reads_env_var(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env-fake")
        embedder = get_embedder("openai")
        assert embedder._api_key == "sk-env-fake"  # type: ignore[attr-defined]

    def test_case_insensitive_dispatch(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        e1 = get_embedder("OpenAI")
        e2 = get_embedder("OPENAI")
        assert e1.name == e2.name == "openai"


# ---------------------------------------------------------------------- #
# OpenAIEmbedder unit behavior with a mocked client
# ---------------------------------------------------------------------- #


class TestOpenAIEmbedderMocked:
    def test_custom_dim_passed_to_api(self, monkeypatch):
        """If dim != 3072, the wrapper must include ``dimensions`` in the API call."""
        from app.embeddings.openai_embed import OpenAIEmbedder

        captured: dict = {}

        class _FakeEmbeddings:
            def create(self, **kwargs):
                captured.update(kwargs)

                class _Resp:
                    data = [
                        type("Item", (), {"embedding": [0.1] * kwargs.get("dimensions", 3072)})()
                        for _ in kwargs["input"]
                    ]

                return _Resp()

        class _FakeClient:
            def __init__(self, *a, **k):
                pass

            embeddings = _FakeEmbeddings()

        embedder = OpenAIEmbedder(api_key="sk-test", dim=256)
        embedder._client = _FakeClient()  # skip _ensure_loaded

        vecs = embedder.encode(["hello", "world"])
        assert captured["model"] == "text-embedding-3-large"
        assert captured["dimensions"] == 256
        assert vecs.shape == (2, 256)
        # Still normalized.
        norms = np.linalg.norm(vecs, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-5)

    def test_full_dim_omits_dimensions_param(self, monkeypatch):
        from app.embeddings.openai_embed import OpenAIEmbedder

        captured: dict = {}

        class _FakeEmbeddings:
            def create(self, **kwargs):
                captured.update(kwargs)

                class _Resp:
                    data = [type("Item", (), {"embedding": [0.1] * 3072})()]

                return _Resp()

        class _FakeClient:
            embeddings = _FakeEmbeddings()

        embedder = OpenAIEmbedder(api_key="sk-test")  # default dim=3072
        embedder._client = _FakeClient()

        embedder.encode(["hello"])
        assert "dimensions" not in captured


# Silence the RUN_SLOW_TESTS reference lint — we read it from env in other test files.
_ = os.getenv("RUN_SLOW_TESTS", "0")
