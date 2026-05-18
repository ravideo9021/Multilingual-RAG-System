"""Real BGE-M3 end-to-end smoke test.

Gated behind ``RUN_SLOW_TESTS=1`` because the model is ~2.3 GB and takes
a few seconds to load + encode even on CPU. Skipped by default.

Run with::

    RUN_SLOW_TESTS=1 pytest tests/test_bge_m3_smoke.py -v
"""

from __future__ import annotations

import os

import numpy as np
import pytest

RUN_SLOW = os.getenv("RUN_SLOW_TESTS", "0") == "1"

pytestmark = pytest.mark.skipif(
    not RUN_SLOW,
    reason="Slow test: set RUN_SLOW_TESTS=1 to run BGE-M3 real-model tests",
)


def test_bge_m3_encodes_hindi_english_to_1024d():
    """One real encode call — verifies the wrapper works end-to-end."""
    from app.embeddings import get_embedder

    embedder = get_embedder("bge-m3", device="cpu")
    assert embedder.name == "bge-m3"
    assert embedder.dim == 1024

    texts = [
        "भारत एक विशाल देश है।",
        "India is a country in South Asia.",
    ]
    vecs = embedder.encode(texts)

    assert vecs.shape == (2, 1024)
    assert vecs.dtype == np.float32

    # L2-normalized.
    norms = np.linalg.norm(vecs, axis=1)
    np.testing.assert_allclose(norms, 1.0, atol=1e-4)

    # Cross-lingual alignment: the Hindi and English sentences describe the
    # same concept, so their cosine similarity should be meaningfully positive.
    # We don't assert a tight threshold (the model is multilingual but not
    # perfect on short text), just that it clears a low bar.
    cos = float(vecs[0] @ vecs[1])
    assert cos > 0.3, f"Expected cross-lingual similarity > 0.3, got {cos:.3f}"


def test_bge_m3_query_passage_methods_work():
    """encode_queries / encode_passages default to encode — exercise them."""
    from app.embeddings import get_embedder

    embedder = get_embedder("bge-m3", device="cpu")
    q = embedder.encode_queries(["What is the capital of India?"])
    p = embedder.encode_passages(["New Delhi is the capital of India."])
    assert q.shape == (1, 1024)
    assert p.shape == (1, 1024)
    # They should be reasonably aligned.
    cos = float(q[0] @ p[0])
    assert cos > 0.3
