"""Tests for :mod:`app.config` — specifically the path-anchoring contract.

The user-facing promise: the app works from any CWD, and all path settings
resolve to absolute locations under ``backend/``. This test file protects
that invariant so nobody accidentally reintroduces CWD-sensitive defaults.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.config import Settings


_PATH_FIELDS = ("data_dir", "models_dir", "index_dir", "fasttext_model_path")


def test_default_paths_are_absolute():
    s = Settings()
    for field in _PATH_FIELDS:
        p = getattr(s, field)
        assert p.is_absolute(), f"{field} default should be absolute, got {p}"


def test_default_paths_under_backend_root():
    """All defaults must live under ``<repo>/multilingual-rag/backend/``."""
    s = Settings()
    # Detect backend root from the config file itself — same trick the code uses.
    import app.config as cfg_mod

    backend_root = Path(cfg_mod.__file__).resolve().parent.parent
    for field in _PATH_FIELDS:
        p = getattr(s, field)
        assert backend_root in p.parents or backend_root == p.parent, (
            f"{field}={p} is not under backend root {backend_root}"
        )


def test_relative_env_override_is_anchored_to_backend(monkeypatch, tmp_path):
    """A relative override via env var must be resolved against ``backend/``."""
    monkeypatch.setenv("DATA_DIR", "my_custom_data")
    s = Settings()

    import app.config as cfg_mod
    backend_root = Path(cfg_mod.__file__).resolve().parent.parent

    assert s.data_dir.is_absolute()
    assert s.data_dir == backend_root / "my_custom_data"


def test_absolute_env_override_passes_through(monkeypatch, tmp_path):
    """An absolute override should NOT be re-rooted under backend/."""
    monkeypatch.setenv("FASTTEXT_MODEL_PATH", str(tmp_path / "lid.bin"))
    s = Settings()
    assert s.fasttext_model_path == tmp_path / "lid.bin"


def test_paths_stable_across_cwd_changes(tmp_path, monkeypatch):
    """Changing CWD must not change what the default paths resolve to."""
    s1 = Settings()
    original_paths = {f: getattr(s1, f) for f in _PATH_FIELDS}

    monkeypatch.chdir(tmp_path)
    s2 = Settings()
    for field in _PATH_FIELDS:
        assert getattr(s2, field) == original_paths[field], (
            f"{field} changed after chdir: was {original_paths[field]}, now {getattr(s2, field)}"
        )


def test_fasttext_model_path_resolves_to_existing_models_dir():
    """The fasttext model path should live inside ``models_dir``
    regardless of what either field's value is."""
    s = Settings()
    assert s.fasttext_model_path.parent == s.models_dir
