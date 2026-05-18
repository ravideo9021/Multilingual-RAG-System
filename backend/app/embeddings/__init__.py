"""Embedding model wrappers."""

from app.embeddings.base import EmbeddingModel, resolve_device
from app.embeddings.factory import SUPPORTED_EMBEDDERS, get_embedder

__all__ = [
    "EmbeddingModel",
    "SUPPORTED_EMBEDDERS",
    "get_embedder",
    "resolve_device",
]
