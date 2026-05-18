"""multilingual-e5-large embedding wrapper via sentence-transformers.

E5 requires distinct ``"query: "`` and ``"passage: "`` prefixes for asymmetric
retrieval — the wrapper handles this automatically.

Model: https://huggingface.co/intfloat/multilingual-e5-large
"""

from __future__ import annotations

import logging
from typing import Literal

import numpy as np

from app.embeddings.base import EmbeddingModel, resolve_device

logger = logging.getLogger(__name__)


class E5Embedder(EmbeddingModel):
    """multilingual-e5-large wrapper (1024-dim).

    Parameters
    ----------
    device:
        Torch device preference.
    model_id:
        HuggingFace model ID. Override for local paths or other e5 variants.
    """

    name = "e5"

    def __init__(
        self,
        device: Literal["auto", "cpu", "cuda", "mps"] = "auto",
        model_id: str = "intfloat/multilingual-e5-large",
    ) -> None:
        self._device = resolve_device(device)
        self._model_id = model_id
        self._model = None  # lazy

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        logger.info(
            "Loading E5 model %s on %s — this downloads ~2.2 GB on first run",
            self._model_id, self._device,
        )
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(self._model_id, device=self._device)

    @property
    def dim(self) -> int:
        return 1024

    # ------------------------------------------------------------------ #
    # Encoding (with prefix handling)
    # ------------------------------------------------------------------ #

    def _encode_with_prefix(
        self,
        texts: list[str],
        prefix: str,
        batch_size: int,
        show_progress: bool,
    ) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        self._ensure_loaded()
        prefixed = [f"{prefix}{t}" for t in texts]
        vecs = self._model.encode(
            prefixed,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return np.asarray(vecs, dtype=np.float32)

    def encode(
        self,
        texts: list[str],
        *,
        batch_size: int = 32,
        show_progress: bool = False,
    ) -> np.ndarray:
        """Default encoding uses the passage prefix.

        Callers that want query-side encoding should use
        :pymeth:`encode_queries` instead.
        """
        return self.encode_passages(texts, batch_size=batch_size, show_progress=show_progress)

    def encode_queries(
        self,
        queries: list[str],
        *,
        batch_size: int = 32,
        show_progress: bool = False,
    ) -> np.ndarray:
        return self._encode_with_prefix(queries, "query: ", batch_size, show_progress)

    def encode_passages(
        self,
        passages: list[str],
        *,
        batch_size: int = 32,
        show_progress: bool = False,
    ) -> np.ndarray:
        return self._encode_with_prefix(passages, "passage: ", batch_size, show_progress)
