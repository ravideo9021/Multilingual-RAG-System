"""LLM provider factory with auto-fallback.

``get_llm()`` reads the configured provider from :pyattr:`settings.llm_provider`
and tries to instantiate it. If the primary provider fails (missing API key,
import error, first-call API error), it silently falls back to the other
provider. If both fail, it raises. The rest of the codebase never needs to
know which backend answered.

The OpenAI provider supports a custom ``base_url`` (via
:pyattr:`settings.openai_base_url`) so it can transparently route through
OpenRouter, Together, Groq, etc. — anything OpenAI-compatible.

``get_llm_cheap()`` returns the "cheap" model variant for lightweight tasks
(translation, rewriting).
"""

from __future__ import annotations

import logging

from app.config import settings
from app.generation.llm_base import LLMProvider

logger = logging.getLogger(__name__)


class LLMInitError(RuntimeError):
    """Raised when no LLM provider could be initialized."""


def _try_gemini(model: str) -> LLMProvider | None:
    key = settings.gemini_api_key
    if not key:
        logger.info("Gemini API key not set — skipping Gemini")
        return None
    try:
        from app.generation.gemini_provider import GeminiProvider

        return GeminiProvider(model, api_key=key)
    except Exception as exc:
        logger.warning("Gemini init failed (%s) — will try fallback", exc)
        return None


def _try_openai(model: str) -> LLMProvider | None:
    key = settings.openai_api_key
    if not key:
        logger.info("OpenAI API key not set — skipping OpenAI")
        return None
    try:
        from app.generation.openai_provider import OpenAIProvider

        return OpenAIProvider(
            model,
            api_key=key,
            base_url=settings.openai_base_url,
        )
    except Exception as exc:
        logger.warning("OpenAI init failed (%s) — will try fallback", exc)
        return None


def get_llm(provider: str | None = None) -> LLMProvider:
    """Return an LLM provider, falling back automatically.

    Parameters
    ----------
    provider:
        Force a specific provider (``"gemini"`` or ``"openai"``). If *None*,
        uses ``settings.llm_provider`` and falls back on failure.

    Raises
    ------
    LLMInitError
        If neither provider could be initialized.
    """
    pref = provider or settings.llm_provider

    if pref == "gemini":
        llm = _try_gemini(settings.gemini_main_model)
        if llm:
            return llm
        llm = _try_openai(settings.openai_main_model)
        if llm:
            logger.info("Fell back to OpenAI (%s)", settings.openai_main_model)
            return llm
    else:
        llm = _try_openai(settings.openai_main_model)
        if llm:
            return llm
        llm = _try_gemini(settings.gemini_main_model)
        if llm:
            logger.info("Fell back to Gemini (%s)", settings.gemini_main_model)
            return llm

    raise LLMInitError(
        "No LLM provider available. Set OPENAI_API_KEY (with optional "
        "OPENAI_BASE_URL for OpenRouter) or GEMINI_API_KEY."
    )


def get_llm_cheap(provider: str | None = None) -> LLMProvider:
    """Return the "cheap" model variant (for translation, rewriting, etc.).

    Falls back the same way as :func:`get_llm`.
    """
    pref = provider or settings.llm_provider

    if pref == "gemini":
        llm = _try_gemini(settings.gemini_cheap_model)
        if llm:
            return llm
        llm = _try_openai(settings.openai_cheap_model)
        if llm:
            logger.info("Fell back to OpenAI cheap (%s)", settings.openai_cheap_model)
            return llm
    else:
        llm = _try_openai(settings.openai_cheap_model)
        if llm:
            return llm
        llm = _try_gemini(settings.gemini_cheap_model)
        if llm:
            logger.info("Fell back to Gemini cheap (%s)", settings.gemini_cheap_model)
            return llm

    raise LLMInitError(
        "No LLM provider available for cheap model. "
        "Set OPENAI_API_KEY or GEMINI_API_KEY."
    )
