"""RAG answer generator — turns retrieved passages + query into a streamed answer.

The generator:

1. Takes the user query + retrieved source passages.
2. Builds a prompt via :mod:`app.generation.prompts`.
3. Calls the LLM (sync or streaming).
4. Returns the answer (and the list of cited source indices, extracted post-hoc).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from app.generation.llm_base import LLMProvider
from app.generation.prompts import (
    CHAT_FALLBACK_PREFIX_EN,
    CHAT_FALLBACK_PREFIX_HI,
    CHAT_SYSTEM_PROMPT,
    NO_ANSWER_TEMPLATE,
    NO_ANSWER_TEMPLATE_HI,
    RAG_SYSTEM_PROMPT,
    build_rag_prompt,
)

logger = logging.getLogger(__name__)

_CITATION_RE = re.compile(r"[\[【](\d+)[\]】]")


@dataclass
class GenerationResult:
    """Outcome of a single RAG generation call."""

    answer: str
    sources: list[dict[str, Any]]
    cited_indices: list[int] = field(default_factory=list)
    language: str = "en"
    model: str = ""


def extract_citations(text: str, max_source: int) -> list[int]:
    """Extract unique cited source indices from the answer text.

    Returns sorted, 1-indexed indices that appear in the text as [N]
    and are within ``[1, max_source]``.
    """
    indices = set()
    for match in _CITATION_RE.finditer(text):
        idx = int(match.group(1))
        if 1 <= idx <= max_source:
            indices.add(idx)
    return sorted(indices)


class RAGGenerator:
    """Generate answers grounded in retrieved passages.

    Parameters
    ----------
    llm:
        The main LLM provider instance.
    """

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def generate(
        self,
        query: str,
        sources: list[dict[str, Any]],
        *,
        language: str = "en",
    ) -> GenerationResult:
        """Synchronous RAG generation."""
        if not sources:
            answer = NO_ANSWER_TEMPLATE_HI if language == "hi" else NO_ANSWER_TEMPLATE
            return GenerationResult(
                answer=answer,
                sources=[],
                cited_indices=[],
                language=language,
                model=self._llm.model,
            )

        prompt = build_rag_prompt(query, sources)
        answer = self._llm.generate(prompt, system=RAG_SYSTEM_PROMPT)
        cited = extract_citations(answer, len(sources))

        return GenerationResult(
            answer=answer,
            sources=sources,
            cited_indices=cited,
            language=language,
            model=self._llm.model,
        )

    async def stream(
        self,
        query: str,
        sources: list[dict[str, Any]],
        *,
        language: str = "en",
    ) -> AsyncIterator[str]:
        """Async streaming RAG generation. Yields text chunks."""
        if not sources:
            answer = NO_ANSWER_TEMPLATE_HI if language == "hi" else NO_ANSWER_TEMPLATE
            yield answer
            return

        prompt = build_rag_prompt(query, sources)
        async for chunk in self._llm.stream(prompt, system=RAG_SYSTEM_PROMPT):
            yield chunk

    async def chat_stream(
        self,
        query: str,
        *,
        language: str = "en",
    ) -> AsyncIterator[str]:
        """Stream a direct LLM answer with no retrieval — chat-only mode.

        Used when the index is empty. The model isn't constrained to any
        passages and behaves as a general-purpose multilingual assistant.
        """
        async for chunk in self._llm.stream(query, system=CHAT_SYSTEM_PROMPT):
            yield chunk

    async def fallback_stream(
        self,
        query: str,
        *,
        language: str = "en",
    ) -> AsyncIterator[str]:
        """Stream a "no relevant docs found, but here's what I know" answer.

        Emits a short prefix telling the user the answer isn't grounded in
        their documents, then streams a general LLM answer.
        """
        prefix = CHAT_FALLBACK_PREFIX_HI if language == "hi" else CHAT_FALLBACK_PREFIX_EN
        yield prefix
        async for chunk in self._llm.stream(query, system=CHAT_SYSTEM_PROMPT):
            yield chunk
