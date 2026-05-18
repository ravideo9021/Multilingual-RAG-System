"""Prompt templates for RAG generation.

All prompts are plain strings — no templating engine. The generator
formats them with ``.format()`` at call time.
"""

from __future__ import annotations

# ---------------------------------------------------------------------- #
# System prompt — injected as the system/developer message.
# ---------------------------------------------------------------------- #

RAG_SYSTEM_PROMPT = """\
You are a helpful multilingual research assistant. You are given retrieved
passages from the user's documents to use as primary context. Follow these
rules:

1. When the passages contain a direct answer or relevant facts, ground your
   answer in them and cite using bracketed numbers like [1], [2], etc.
2. When the passages contain only questions, topics, headings, or partial
   information rather than answers, use your own knowledge to answer the
   user — be genuinely helpful, do not refuse. Cite [N] only for claims
   actually drawn from the passages; uncited statements are general knowledge.
3. If a claim is partly from the passages and partly from general knowledge,
   cite the passage and add the rest as supplementary explanation.
4. Respond in the SAME LANGUAGE as the user's question. Hindi → Hindi,
   English → English.
5. Be concise but thorough. Prefer direct answers over preambles.
6. Only say "I don't know" if you genuinely don't know AND the passages
   don't help — never refuse just because the passages lack the answer.
"""

# ---------------------------------------------------------------------- #
# User prompt — the actual query with context passages injected.
# ---------------------------------------------------------------------- #

RAG_USER_PROMPT = """\
Context passages:
{context}

Question: {query}
"""


def format_context(sources: list[dict]) -> str:
    """Format retrieved passages as numbered context for the LLM.

    Each passage is rendered as::

        [1] (source) title
        text...

    Parameters
    ----------
    sources:
        List of retrieval hit dicts, each with at least a ``text`` key.
        Optional keys: ``title``, ``source``, ``language``.
    """
    parts: list[str] = []
    for i, src in enumerate(sources, start=1):
        header_parts: list[str] = []
        if src.get("source"):
            header_parts.append(f"({src['source']})")
        if src.get("title"):
            header_parts.append(src["title"])
        header = " ".join(header_parts) if header_parts else f"Passage {i}"
        parts.append(f"[{i}] {header}\n{src.get('text', '')}")
    return "\n\n".join(parts)


def build_rag_prompt(query: str, sources: list[dict]) -> str:
    """Build the full user-side prompt for RAG generation."""
    context = format_context(sources)
    return RAG_USER_PROMPT.format(context=context, query=query)


# ---------------------------------------------------------------------- #
# No-answer template — used when threshold gating returns 0 passages.
# ---------------------------------------------------------------------- #

NO_ANSWER_TEMPLATE = (
    "I could not find relevant information in the knowledge base to answer "
    "your question. Please try rephrasing, or ask about a different topic "
    "covered in the indexed documents."
)

NO_ANSWER_TEMPLATE_HI = (
    "मुझे आपके प्रश्न का उत्तर देने के लिए ज्ञान आधार में प्रासंगिक जानकारी "
    "नहीं मिली। कृपया अपना प्रश्न दोबारा बनाएं, या अनुक्रमित दस्तावेज़ों में "
    "शामिल किसी अन्य विषय के बारे में पूछें।"
)

# ---------------------------------------------------------------------- #
# Chat-only system prompts — used when the index is empty (no documents
# uploaded) or when retrieval found nothing relevant. The system should
# still be helpful, just without the "ground in passages" constraint.
# ---------------------------------------------------------------------- #

CHAT_SYSTEM_PROMPT = """\
You are a helpful multilingual assistant. Answer the user's question clearly
and concisely.

- Respond in the SAME LANGUAGE as the user's question. If the question is in
  Hindi, answer in Hindi. If in English, answer in English.
- Be direct and useful — no unnecessary preamble.
- If you don't know something, say so honestly.
"""

CHAT_FALLBACK_PREFIX_EN = (
    "I couldn't find specific information about this in your documents, "
    "but here's what I know:\n\n"
)

CHAT_FALLBACK_PREFIX_HI = (
    "आपके दस्तावेज़ों में इस विषय पर विशिष्ट जानकारी नहीं मिली, "
    "लेकिन सामान्य ज्ञान के आधार पर:\n\n"
)

# ---------------------------------------------------------------------- #
# Translation prompt — used by the LLM-backed translator.
# ---------------------------------------------------------------------- #

TRANSLATE_SYSTEM_PROMPT = """\
You are a precise translator. Translate the given text to the target language.
Output ONLY the translation, nothing else — no explanations, no preamble.
Preserve the meaning and tone. If the text is already in the target language,
return it unchanged.
"""

TRANSLATE_USER_PROMPT = """\
Translate the following text to {target_language}:

{text}
"""
