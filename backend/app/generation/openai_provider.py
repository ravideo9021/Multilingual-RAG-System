"""OpenAI-compatible LLM provider.

Uses the ``openai`` Python SDK. Supports sync generation and async
streaming with exponential backoff on rate-limit / transient errors.

Setting ``base_url`` to ``https://openrouter.ai/api/v1`` (or any other
OpenAI-compatible gateway) lets this provider talk to OpenRouter, Together,
Groq, etc. without changing call sites.
"""

from __future__ import annotations

import logging
import time
from typing import AsyncIterator

from app.generation.llm_base import LLMProvider

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_INITIAL_BACKOFF = 1.0  # seconds


class OpenAIProvider(LLMProvider):
    """OpenAI-backed LLM provider.

    Parameters
    ----------
    model:
        Model name, e.g. ``"gpt-4o"`` or ``"deepseek/deepseek-chat-v3-0324:free"``.
    api_key:
        API key (OpenAI key, or OpenRouter key if ``base_url`` points there).
    base_url:
        Optional override for the API endpoint. ``None`` (default) talks to
        OpenAI; ``"https://openrouter.ai/api/v1"`` routes through OpenRouter.
    """

    def __init__(
        self,
        model: str,
        *,
        api_key: str,
        base_url: str | None = None,
    ) -> None:
        super().__init__(model)
        import openai

        client_kwargs: dict[str, object] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
            # OpenRouter recommends these headers for routing/leaderboards.
            client_kwargs["default_headers"] = {
                "HTTP-Referer": "https://github.com/multilingual-rag",
                "X-Title": "Multilingual RAG System",
            }

        self._client = openai.OpenAI(**client_kwargs)  # type: ignore[arg-type]
        self._async_client = openai.AsyncOpenAI(**client_kwargs)  # type: ignore[arg-type]
        self._openai = openai
        logger.info(
            "OpenAIProvider initialized with model=%s base_url=%s",
            model, base_url or "<default OpenAI>",
        )

    def _build_messages(
        self, prompt: str, system: str | None
    ) -> list[dict[str, str]]:
        msgs: list[dict[str, str]] = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
        return msgs

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.3,
    ) -> str:
        messages = self._build_messages(prompt, system)
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=temperature,
                )
                return response.choices[0].message.content or ""
            except self._openai.RateLimitError as exc:
                last_exc = exc
                wait = _INITIAL_BACKOFF * (2 ** attempt)
                logger.warning(
                    "OpenAI generate rate-limited (attempt %d/%d), retrying in %.1fs",
                    attempt + 1, _MAX_RETRIES, wait,
                )
                time.sleep(wait)
            except self._openai.APIStatusError as exc:
                last_exc = exc
                if exc.status_code in (500, 502, 503, 529):
                    wait = _INITIAL_BACKOFF * (2 ** attempt)
                    logger.warning(
                        "OpenAI generate %d (attempt %d/%d), retrying in %.1fs",
                        exc.status_code, attempt + 1, _MAX_RETRIES, wait,
                    )
                    time.sleep(wait)
                else:
                    raise
        raise last_exc  # type: ignore[misc]

    async def stream(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.3,
    ) -> AsyncIterator[str]:
        import asyncio

        messages = self._build_messages(prompt, system)
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = await self._async_client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=temperature,
                    stream=True,
                )
                async for chunk in response:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if delta and delta.content:
                        yield delta.content
                return
            except self._openai.RateLimitError as exc:
                last_exc = exc
                wait = _INITIAL_BACKOFF * (2 ** attempt)
                logger.warning(
                    "OpenAI stream rate-limited (attempt %d/%d), retrying in %.1fs",
                    attempt + 1, _MAX_RETRIES, wait,
                )
                await asyncio.sleep(wait)
            except self._openai.APIStatusError as exc:
                last_exc = exc
                if exc.status_code in (500, 502, 503, 529):
                    wait = _INITIAL_BACKOFF * (2 ** attempt)
                    logger.warning(
                        "OpenAI stream %d (attempt %d/%d), retrying in %.1fs",
                        exc.status_code, attempt + 1, _MAX_RETRIES, wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    raise
        raise last_exc  # type: ignore[misc]
