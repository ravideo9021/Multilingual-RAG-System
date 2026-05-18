"""Abstract base class for all embedding models.

Every embedder — BGE-M3, multilingual-e5, OpenAI — implements this interface
so the rest of the pipeline can swap models without changing calling code.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal

import numpy as np

logger = logging.getLogger(__name__)


def resolve_device(preference: Literal["auto", "cpu", "cuda", "mps"] = "auto") -> str:
    """Pick the best available torch device.

    * ``"auto"`` — CUDA > MPS > CPU (in that order).
    * ``"cuda"`` / ``"mps"`` — use if available, else fall back to CPU with a warning.
    * ``"cpu"`` — always CPU.

    Returns a string suitable for ``torch.device()``.
    """
    if preference == "cpu":
        return "cpu"

    try:
        import torch
    except ImportError:
        logger.warning("torch not installed — falling back to CPU")
        return "cpu"

    if preference in ("auto", "cuda"):
        if torch.cuda.is_available():
            return "cuda"
        if preference == "cuda":
            logger.warning("CUDA requested but not available — falling back to CPU")

    if preference in ("auto", "mps"):
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        if preference == "mps":
            logger.warning("MPS requested but not available — falling back to CPU")

    return "cpu"


class EmbeddingModel(ABC):
    """Uniform interface over dense embedding models.

    Subclasses MUST set :pyattr:`name` and implement :pymeth:`encode`.
    They MAY override :pymeth:`encode_queries` / :pymeth:`encode_passages`
    if the model needs distinct prompts for each role (e.g., E5 uses
    ``"query: "`` / ``"passage: "`` prefixes).
    """

    name: str  # short identifier, e.g. "bge-m3"

    @property
    @abstractmethod
    def dim(self) -> int:
        """Dimensionality of the dense output vectors."""

    @abstractmethod
    def encode(
        self,
        texts: list[str],
        *,
        batch_size: int = 32,
        show_progress: bool = False,
    ) -> np.ndarray:
        """Encode a list of texts into a ``(N, dim)`` float32 array.

        Results MUST be L2-normalized so cosine similarity = inner product.
        """

    def encode_queries(
        self,
        queries: list[str],
        *,
        batch_size: int = 32,
        show_progress: bool = False,
    ) -> np.ndarray:
        """Encode *queries* (may add model-specific prefixes)."""
        return self.encode(queries, batch_size=batch_size, show_progress=show_progress)

    def encode_passages(
        self,
        passages: list[str],
        *,
        batch_size: int = 32,
        show_progress: bool = False,
    ) -> np.ndarray:
        """Encode *passages* (may add model-specific prefixes)."""
        return self.encode(passages, batch_size=batch_size, show_progress=show_progress)

    # ------------------------------------------------------------------ #
    # Disk cache helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def save_embeddings(
        embeddings: np.ndarray,
        metadata: list[dict],
        path: Path,
    ) -> None:
        """Persist embeddings + metadata to disk.

        Writes two files:
        * ``<path>.npy``  — the ``(N, dim)`` float32 array
        * ``<path>.meta.json`` — the list of per-row metadata dicts

        ``path`` should NOT include a file extension.
        """
        import json

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        npy_path = path.with_suffix(".npy")
        meta_path = path.with_name(path.name + ".meta.json")

        np.save(npy_path, embeddings)
        meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Saved %d embeddings to %s", len(embeddings), npy_path)

    @staticmethod
    def load_embeddings(path: Path) -> tuple[np.ndarray, list[dict]]:
        """Load previously saved embeddings + metadata.

        ``path`` should NOT include a file extension (mirrors :pymeth:`save_embeddings`).

        Returns ``(embeddings, metadata)`` where embeddings is ``(N, dim)``
        float32 and metadata is the corresponding list of dicts.

        Raises ``FileNotFoundError`` if either file is missing.
        """
        import json

        path = Path(path)
        npy_path = path.with_suffix(".npy")
        meta_path = path.with_name(path.name + ".meta.json")

        embeddings = np.load(npy_path)
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        logger.info("Loaded %d embeddings from %s", len(embeddings), npy_path)
        return embeddings, metadata
