"""Tests for prompts, generator, and translator.

All LLM calls are mocked — zero real API calls.
"""

from __future__ import annotations

from typing import AsyncIterator
from unittest.mock import MagicMock

import pytest

from app.generation.generator import GenerationResult, RAGGenerator, extract_citations
from app.generation.llm_base import LLMProvider
from app.generation.prompts import (
    NO_ANSWER_TEMPLATE,
    NO_ANSWER_TEMPLATE_HI,
    build_rag_prompt,
    format_context,
)
from app.generation.translator import LLMTranslator


# ---------------------------------------------------------------------- #
# Mock LLM
# ---------------------------------------------------------------------- #


class _MockLLM(LLMProvider):
    """Deterministic mock LLM for unit tests."""

    def __init__(self, response: str = "Mock answer [1].", model: str = "mock-model"):
        super().__init__(model)
        self._response = response
        self.last_prompt: str | None = None
        self.last_system: str | None = None

    def generate(self, prompt, *, system=None, temperature=0.3):
        self.last_prompt = prompt
        self.last_system = system
        return self._response

    async def stream(self, prompt, *, system=None, temperature=0.3):
        self.last_prompt = prompt
        self.last_system = system
        for word in self._response.split(" "):
            yield word + " "


# ---------------------------------------------------------------------- #
# Prompts
# ---------------------------------------------------------------------- #


class TestFormatContext:
    def test_basic_formatting(self):
        sources = [
            {"text": "India is large.", "source": "wiki", "title": "India"},
            {"text": "भारत बड़ा है।", "source": "wiki", "title": "भारत"},
        ]
        ctx = format_context(sources)
        assert "[1] (wiki) India" in ctx
        assert "India is large." in ctx
        assert "[2] (wiki) भारत" in ctx

    def test_missing_source_and_title(self):
        sources = [{"text": "Hello world"}]
        ctx = format_context(sources)
        assert "[1] Passage 1" in ctx

    def test_empty_sources(self):
        assert format_context([]) == ""


class TestBuildRagPrompt:
    def test_contains_query_and_context(self):
        sources = [{"text": "The capital is Delhi.", "title": "India"}]
        prompt = build_rag_prompt("What is the capital?", sources)
        assert "What is the capital?" in prompt
        assert "The capital is Delhi." in prompt
        assert "[1]" in prompt


# ---------------------------------------------------------------------- #
# Citation extraction
# ---------------------------------------------------------------------- #


class TestExtractCitations:
    def test_basic(self):
        assert extract_citations("Based on [1] and [3].", max_source=5) == [1, 3]

    def test_dedup_and_sort(self):
        assert extract_citations("[2] [1] [2] [1]", max_source=5) == [1, 2]

    def test_filters_out_of_range(self):
        assert extract_citations("[0] [1] [10]", max_source=3) == [1]

    def test_no_citations(self):
        assert extract_citations("No references here.", max_source=5) == []


# ---------------------------------------------------------------------- #
# RAGGenerator
# ---------------------------------------------------------------------- #


class TestRAGGenerator:
    def test_generate_with_sources(self):
        llm = _MockLLM("Delhi is the capital [1].")
        gen = RAGGenerator(llm)
        sources = [{"text": "Capital of India is Delhi.", "title": "India"}]
        result = gen.generate("What is the capital?", sources, language="en")
        assert isinstance(result, GenerationResult)
        assert "Delhi" in result.answer
        assert result.cited_indices == [1]
        assert result.model == "mock-model"
        assert result.sources == sources

    def test_generate_no_sources_english(self):
        llm = _MockLLM()
        gen = RAGGenerator(llm)
        result = gen.generate("What?", [], language="en")
        assert result.answer == NO_ANSWER_TEMPLATE
        assert result.cited_indices == []

    def test_generate_no_sources_hindi(self):
        llm = _MockLLM()
        gen = RAGGenerator(llm)
        result = gen.generate("क्या?", [], language="hi")
        assert result.answer == NO_ANSWER_TEMPLATE_HI

    @pytest.mark.asyncio
    async def test_stream_with_sources(self):
        llm = _MockLLM("Delhi [1].")
        gen = RAGGenerator(llm)
        sources = [{"text": "Capital is Delhi."}]
        tokens = []
        async for chunk in gen.stream("query", sources, language="en"):
            tokens.append(chunk)
        assert len(tokens) > 0
        full = "".join(tokens)
        assert "Delhi" in full

    @pytest.mark.asyncio
    async def test_stream_no_sources(self):
        llm = _MockLLM()
        gen = RAGGenerator(llm)
        tokens = []
        async for chunk in gen.stream("query", [], language="en"):
            tokens.append(chunk)
        full = "".join(tokens)
        assert full == NO_ANSWER_TEMPLATE


# ---------------------------------------------------------------------- #
# LLMTranslator
# ---------------------------------------------------------------------- #


class TestLLMTranslator:
    def test_translate_calls_llm(self):
        llm = _MockLLM("भारत की राजधानी क्या है?")
        translator = LLMTranslator(llm)
        result = translator.translate_to("What is the capital of India?", "hi")
        assert result == "भारत की राजधानी क्या है?"
        assert llm.last_prompt is not None
        assert "Hindi" in llm.last_prompt

    def test_translate_to_english(self):
        llm = _MockLLM("What is the capital of India?")
        translator = LLMTranslator(llm)
        result = translator.translate_to("भारत की राजधानी", "en")
        assert result == "What is the capital of India?"
        assert "English" in llm.last_prompt

    def test_translate_falls_back_on_error(self):
        llm = MagicMock(spec=LLMProvider)
        llm.generate.side_effect = RuntimeError("API down")
        translator = LLMTranslator(llm)
        result = translator.translate_to("hello", "hi")
        assert result == "hello"  # returns original on error

    def test_translate_falls_back_on_empty_result(self):
        llm = _MockLLM("")
        translator = LLMTranslator(llm)
        result = translator.translate_to("hello", "hi")
        assert result == "hello"

    def test_satisfies_translator_protocol(self):
        from app.retrieval.query_router import Translator

        llm = _MockLLM()
        translator = LLMTranslator(llm)
        assert isinstance(translator, Translator)
