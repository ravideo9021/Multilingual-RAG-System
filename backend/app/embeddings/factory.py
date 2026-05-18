"""Embedder dispatch.

Importing ``BGEM3Embedder`` eagerly pulls in FlagEmbedding + torch (~5 GB),
so each branch imports its wrapper lazily.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.embeddings.base import EmbeddingModel

SUPPORTED_EMBEDDERS = ("bge-m3", "e5", "openai")


def get_embedder(name: str, **kwargs: Any) -> "EmbeddingModel":
    """Return an :class:`EmbeddingModel` by short name.

    Parameters
    ----------
    name:
        One of ``"bge-m3"``, ``"e5"``, ``"openai"`` (case-insensitive).
    **kwargs:
        Passed through to the embedder's constructor.

    Raises
    ------
    ValueError
        If ``name`` isn't a recognized embedder.
    """
    key = name.lower().strip()

    if key == "bge-m3":
        from app.embeddings.bge_m3 import BGEM3Embedder

        return BGEM3Embedder(**kwargs)

    if key == "e5":
        from app.embeddings.e5 import E5Embedder

        return E5Embedder(**kwargs)

    if key == "openai":
        from app.embeddings.openai_embed import OpenAIEmbedder

        return OpenAIEmbedder(**kwargs)

    raise ValueError(
        f"Unknown embedder {name!r}. Supported: {', '.join(SUPPORTED_EMBEDDERS)}"
    )
