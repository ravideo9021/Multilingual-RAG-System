"""LLM-backed translator for the query router's dual-query strategy.

Implements the :class:`app.retrieval.query_router.Translator` protocol
using the cheap LLM model (Gemini Flash / GPT-4o-mini). Falls back to
returning the input unchanged on any error so the retrieval pipeline
never breaks because of a translation failure.
"""

from __future__ import annotations

import logging

from app.generation.llm_base import LLMProvider
from app.generation.prompts import TRANSLATE_SYSTEM_PROMPT, TRANSLATE_USER_PROMPT

logger = logging.getLogger(__name__)

_LANG_NAMES = {
    "hi": "Hindi",
    "en": "English",
    "hinglish": "English",  # Hinglish → translate to clean English
}


class LLMTranslator:
    """Translate text via the cheap LLM model.

    Satisfies the ``Translator`` protocol defined in
    :mod:`app.retrieval.query_router`.

    Parameters
    ----------
    llm:
        An :class:`LLMProvider` instance (typically the cheap model).
    """

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def translate_to(self, text: str, target_lang: str) -> str:
        """Translate ``text`` to ``target_lang``.

        On any error, returns ``text`` unchanged so the pipeline degrades
        gracefully to single-language retrieval rather than failing entirely.
        """
        target_name = _LANG_NAMES.get(target_lang, target_lang)
        prompt = TRANSLATE_USER_PROMPT.format(
            target_language=target_name,
            text=text,
        )
        try:
            result = self._llm.generate(
                prompt,
                system=TRANSLATE_SYSTEM_PROMPT,
                temperature=0.1,
            )
            translated = result.strip()
            if not translated:
                logger.warning("Empty translation result; returning original")
                return text
            logger.debug("Translated [%s→%s]: %s → %s", "auto", target_lang, text[:60], translated[:60])
            return translated
        except Exception as exc:
            logger.warning("Translation failed (%s); returning original text", exc)
            return text
