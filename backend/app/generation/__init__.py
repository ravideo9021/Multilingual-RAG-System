"""LLM generation: providers, prompts, translator, RAG generator."""

from app.generation.factory import LLMInitError, get_llm, get_llm_cheap
from app.generation.generator import GenerationResult, RAGGenerator, extract_citations
from app.generation.llm_base import LLMProvider
from app.generation.prompts import (
    NO_ANSWER_TEMPLATE,
    NO_ANSWER_TEMPLATE_HI,
    RAG_SYSTEM_PROMPT,
    build_rag_prompt,
    format_context,
)
from app.generation.translator import LLMTranslator

__all__ = [
    "GenerationResult",
    "LLMInitError",
    "LLMProvider",
    "LLMTranslator",
    "NO_ANSWER_TEMPLATE",
    "NO_ANSWER_TEMPLATE_HI",
    "RAG_SYSTEM_PROMPT",
    "RAGGenerator",
    "build_rag_prompt",
    "extract_citations",
    "format_context",
    "get_llm",
    "get_llm_cheap",
]
