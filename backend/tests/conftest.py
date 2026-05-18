"""Shared pytest fixtures.

The chunker tests need a tokenizer, which is downloaded once on first use and
cached in HuggingFace's local cache. We expose a session-scoped chunker
fixture so the tokenizer load only happens once across the test session.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# On macOS, torch and faiss-cpu each bundle their own copy of libomp.
# When both are loaded in the same process, OpenMP aborts with "already
# initialized". This env var must be set before either library is imported.
if sys.platform == "darwin":
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

# Make `app` package importable when running pytest from the backend/ dir.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


@pytest.fixture(scope="session")
def small_chunker():
    """A chunker with small chunks (for fast tests that exercise splitting)."""
    from app.ingestion.chunker import ScriptAwareRecursiveChunker

    return ScriptAwareRecursiveChunker(chunk_size=64, overlap=10)


@pytest.fixture(scope="session")
def medium_chunker():
    """A chunker with default-sized chunks."""
    from app.ingestion.chunker import ScriptAwareRecursiveChunker

    return ScriptAwareRecursiveChunker(chunk_size=128, overlap=20)
