"""OpenAI embedding wrapper for benchmark comparison only.

This exists purely so :mod:`app.eval.embedding_compare` can benchmark BGE-M3
and multilingual-e5 against ``text-embedding-3-large``. The main pipeline
uses self-hosted embeddings.
"""

from __future__ import annotations

import logging
import os

import numpy as np

from app.embeddings.base import EmbeddingModel

logger = logging.getLogger(__name__)

# Per OpenAI docs, text-embedding-3-large accepts up to ~2048 inputs per call,
# but 100 is a reasonable batch for latency and cost predictability.
_DEFAULT_BATCH = 100


class OpenAIEmbedder(EmbeddingModel):
    """OpenAI ``text-embedding-3-large`` (3072-dim by default).

    Parameters
    ----------
    api_key:
        OpenAI API key. If ``None``, falls back to the ``OPENAI_API_KEY`` env var.
    model_id:
        Embedding model name.
    dim:
        Output dimensionality. OpenAI v3 models support native dimension
        reduction — leave as 3072 for full quality, or shrink for speed/storage.
    """

    name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        model_id: str = "text-embedding-3-large",
        dim: int = 3072,
    ) -> None:
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self._api_key:
            raise ValueError(
                "OpenAIEmbedder requires an api_key or OPENAI_API_KEY environment variable"
            )
        self._model_id = model_id
        self._dim = dim
        self._client = None  # lazy

    def _ensure_loaded(self) -> None:
        if self._client is not None:
            return
        from openai import OpenAI

        self._client = OpenAI(api_key=self._api_key)

    @property
    def dim(self) -> int:
        return self._dim

    def encode(
        self,
        texts: list[str],
        *,
        batch_size: int = _DEFAULT_BATCH,
        show_progress: bool = False,
    ) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)

        self._ensure_loaded()

        iterator: range | object = range(0, len(texts), batch_size)
        if show_progress:
            from tqdm import tqdm

            iterator = tqdm(iterator, desc=f"openai ({self._model_id})")

        all_vecs: list[list[float]] = []
        for i in iterator:
            batch = texts[i : i + batch_size]
            kwargs: dict = {"model": self._model_id, "input": batch}
            if self._dim != 3072:
                kwargs["dimensions"] = self._dim
            resp = self._client.embeddings.create(**kwargs)
            all_vecs.extend(item.embedding for item in resp.data)

        vecs = np.asarray(all_vecs, dtype=np.float32)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vecs / norms
