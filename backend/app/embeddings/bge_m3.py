"""BGE-M3 embedding wrapper via sentence-transformers.

BGE-M3 is a multilingual, multi-functional, multi-granularity embedding model.
This wrapper exposes the dense-only path (1024-dim) for cosine retrieval,
using sentence-transformers for encoding (which avoids the fork-based
multiprocessing issues that FlagEmbedding's encoder has on macOS).

Model: https://huggingface.co/BAAI/bge-m3
"""

from __future__ import annotations

import logging
from typing import Literal

import numpy as np

from app.embeddings.base import EmbeddingModel, resolve_device

logger = logging.getLogger(__name__)


class BGEM3Embedder(EmbeddingModel):
    """BGE-M3 wrapper using sentence-transformers.

    The underlying model is ~2.3 GB — it's loaded lazily on first encode call.

    Parameters
    ----------
    device:
        Torch device preference. ``"auto"`` picks cuda > mps > cpu.
    use_fp16:
        If True, load in half precision (CUDA only — silently ignored on CPU/MPS
        since fp16 on CPU is slower than fp32). Defaults to True on CUDA, False
        elsewhere.
    max_length:
        Max input tokens per text. BGE-M3 supports up to 8192.
    model_id:
        HuggingFace model ID. Override for local paths or fine-tuned variants.
    """

    name = "bge-m3"

    def __init__(
        self,
        device: Literal["auto", "cpu", "cuda", "mps"] = "auto",
        use_fp16: bool | None = None,
        max_length: int = 8192,
        model_id: str = "BAAI/bge-m3",
    ) -> None:
        self._device = resolve_device(device)
        if use_fp16 is None:
            use_fp16 = self._device == "cuda"
        elif use_fp16 and self._device != "cuda":
            logger.warning("use_fp16=True ignored on %s device", self._device)
            use_fp16 = False
        self._use_fp16 = use_fp16
        self._max_length = max_length
        self._model_id = model_id
        self._model = None  # lazy

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        logger.info(
            "Loading BGE-M3 model %s on %s (fp16=%s) — this downloads ~2.3 GB on first run",
            self._model_id, self._device, self._use_fp16,
        )
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(
            self._model_id,
            device=self._device,
            trust_remote_code=True,
        )
        self._model.max_seq_length = self._max_length

    @property
    def dim(self) -> int:
        return 1024

    def encode(
        self,
        texts: list[str],
        *,
        batch_size: int = 32,
        show_progress: bool = False,
    ) -> np.ndarray:
        """Encode texts to L2-normalized dense vectors.

        BGE-M3 uses the same encoding for queries and passages (no prefixes
        required), so :pymeth:`encode_queries` and :pymeth:`encode_passages`
        both delegate here.
        """
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)

        self._ensure_loaded()
        vecs = self._model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            normalize_embeddings=True,
        )
        return np.asarray(vecs, dtype=np.float32)
