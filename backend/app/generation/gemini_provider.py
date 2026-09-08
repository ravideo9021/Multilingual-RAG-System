"""Google Gemini LLM provider.

Uses the ``google-generativeai`` SDK. Supports sync generation and async
streaming with exponential backoff on rate-limit / transient errors.
"""

from __future__ import annotations

import logging
import time
from typing import AsyncIterator

from app.generation.llm_base import LLMProvider

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_INITIAL_BACKOFF = 1.0  # seconds


class GeminiProvider(LLMProvider):
    """Gemini-backed LLM provider.

    Parameters
    ----------
    model:
        Model name, e.g. ``"gemini-2.5-pro"`` or ``"gemini-2.5-flash"``.
    api_key:
        Google AI API key.
    """

    def __init__(self, model: str, *, api_key: str) -> None:
        super().__init__(model)
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self._genai = genai
        self._api_key = api_key
        logger.info("GeminiProvider initialized with model=%s", model)

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.3,
    ) -> str:
        model = self._genai.GenerativeModel(
            model_name=self._model,
            system_instruction=system,
            generation_config=self._genai.GenerationConfig(temperature=temperature),
        )
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = model.generate_content(prompt)
                return response.text
            except Exception as exc:
                last_exc = exc
                if not self._is_retryable(exc):
                    raise
                wait = _INITIAL_BACKOFF * (2 ** attempt)
                logger.warning(
                    "Gemini generate attempt %d/%d failed (%s), retrying in %.1fs",
                    attempt + 1, _MAX_RETRIES, exc, wait,
                )
                time.sleep(wait)
        raise last_exc  # type: ignore[misc]

    async def stream(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.3,
    ) -> AsyncIterator[str]:
        import asyncio

        model = self._genai.GenerativeModel(
            model_name=self._model,
            system_instruction=system,
            generation_config=self._genai.GenerationConfig(temperature=temperature),
        )

        _SENTINEL = object()
        last_exc: Exception | None = None
        loop = asyncio.get_event_loop()

        for attempt in range(_MAX_RETRIES):
            try:
                aq: asyncio.Queue = asyncio.Queue()

                def _run_sync():
                    try:
                        response = model.generate_content(prompt, stream=True)
                        for chunk in response:
                            if chunk.text:
                                loop.call_soon_threadsafe(aq.put_nowait, chunk.text)
                    except Exception as exc:
                        loop.call_soon_threadsafe(aq.put_nowait, exc)
                    finally:
                        loop.call_soon_threadsafe(aq.put_nowait, _SENTINEL)

                loop.run_in_executor(None, _run_sync)

                while True:
                    item = await aq.get()
                    if item is _SENTINEL:
                        return
                    if isinstance(item, Exception):
                        raise item
                    yield item

            except Exception as exc:
                last_exc = exc
                if not self._is_retryable(exc):
                    raise
                wait = _INITIAL_BACKOFF * (2 ** attempt)
                logger.warning(
                    "Gemini stream attempt %d/%d failed (%s), retrying in %.1fs",
                    attempt + 1, _MAX_RETRIES, exc, wait,
                )
                await asyncio.sleep(wait)
        raise last_exc  # type: ignore[misc]

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        """True for rate-limit / transient server errors."""
        exc_str = str(exc).lower()
        retryable_signals = ["429", "rate", "resource_exhausted", "503", "500", "overloaded"]
        return any(sig in exc_str for sig in retryable_signals)
