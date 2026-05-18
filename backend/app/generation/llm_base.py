"""Abstract base class for LLM providers.

Both sync ``generate`` and async ``stream`` methods must be implemented.
The factory (``generation/factory.py``) dispatches to the correct provider
based on config and available API keys.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import AsyncIterator

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Uniform interface over LLM backends (Gemini, OpenAI, …).

    Parameters
    ----------
    model:
        Model identifier (e.g., ``"gemini-2.5-pro"``, ``"gpt-4o"``).
    """

    def __init__(self, model: str) -> None:
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.3,
    ) -> str:
        """Synchronous single-turn generation. Returns the full response text."""

    @abstractmethod
    async def stream(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.3,
    ) -> AsyncIterator[str]:
        """Async token-level streaming. Yields text chunks as they arrive."""
        # This method is an async generator — the `yield` below is required
        # to make it a valid AsyncIterator even in the ABC stub.
        yield ""  # pragma: no cover
        raise NotImplementedError  # pragma: no cover
