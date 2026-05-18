"""Query router — glue between classifier, translator, retriever, RRF, threshold.

Given a raw user query, decides how to retrieve:

* **Pure Hindi (``hi``)** or **English (``en``)** → single retrieval pass.
  Cross-lingual alignment in the embedder (BGE-M3, multilingual-e5) handles
  the language mismatch against the corpus.
* **Hinglish** or **mixed** → dual-query strategy. Translate the query to
  both ``hi`` and ``en``, retrieve against each, then fuse with Reciprocal
  Rank Fusion. This compensates for embedder weakness on romanized Hindi.
* **Other** → single pass; cross-lingual alignment will do what it can.

The actual translation is deferred to a :class:`Translator` protocol — the
router does not depend on any LLM. Chunk E will provide a real LLM-backed
translator; Chunk C ships with :class:`IdentityTranslator` (no-op) so the
router is testable and usable end-to-end immediately.

Threshold gating is applied to the **pre-fusion** per-query results, since
fused RRF scores are rank-based sums and not comparable to cosine
similarity. The fused list is then truncated to ``top_k``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from app.retrieval.language_classifier import LanguageClassifier, LanguageResult
from app.retrieval.retriever import DenseRetriever
from app.retrieval.rrf import reciprocal_rank_fusion
from app.retrieval.threshold import apply_threshold

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------- #
# Translator protocol
# ---------------------------------------------------------------------- #


@runtime_checkable
class Translator(Protocol):
    """Translate a string into another language.

    Implementations:

    * :class:`IdentityTranslator` — no-op, returns the input unchanged.
      Used in Chunk C tests and as a default until the LLM is wired up.
    * The LLM-backed translator built in Chunk E, which calls Gemini
      (or OpenAI, on fallback) and does real translation.
    """

    def translate_to(self, text: str, target_lang: str) -> str:
        """Translate ``text`` into ``target_lang`` (ISO 639-1, e.g., ``"hi"``).

        Implementations MUST NOT raise on unsupported languages — they should
        return the input unchanged as a safe fallback.
        """
        ...


class IdentityTranslator:
    """No-op translator. Returns input unchanged regardless of target language.

    Useful as a default and for tests. Real cross-lingual retrieval still
    works under an identity translator because the embedders (BGE-M3,
    multilingual-e5) are cross-lingual by construction — the dual-query
    strategy without translation degenerates to issuing the same query
    twice, which is harmless but doesn't *add* lift. The LLM-backed
    translator in Chunk E gives the real multilingual boost.
    """

    def translate_to(self, text: str, target_lang: str) -> str:
        return text


# ---------------------------------------------------------------------- #
# Routed result
# ---------------------------------------------------------------------- #


@dataclass
class RoutedResult:
    """Outcome of a single routed query.

    Attributes
    ----------
    results:
        Final list of hits, already thresholded and truncated to ``top_k``.
    language:
        The classifier's label for the input query.
    language_confidence:
        Classifier confidence.
    strategy:
        Which retrieval path was taken — ``"direct"`` (single pass) or
        ``"dual"`` (two passes fused via RRF).
    queries_used:
        The actual query strings sent to the embedder. One entry for
        ``"direct"``, two for ``"dual"``.
    """

    results: list[dict[str, Any]]
    language: str
    language_confidence: float
    strategy: str  # "direct" | "dual"
    queries_used: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------- #
# Router
# ---------------------------------------------------------------------- #


class QueryRouter:
    """Route a query through classify → (translate) → retrieve → threshold → fuse.

    Parameters
    ----------
    classifier:
        :class:`LanguageClassifier` instance.
    retriever:
        :class:`DenseRetriever` instance.
    translator:
        Any :class:`Translator` implementation. Defaults to
        :class:`IdentityTranslator` (no-op) if not supplied.
    top_k:
        Number of hits to return in :pyattr:`RoutedResult.results`.
    per_query_k:
        Number of hits pulled from each retrieval pass before fusion /
        threshold. Defaults to ``2 * top_k`` so RRF has a reasonable pool.
    threshold:
        Minimum cosine score to keep a hit, applied pre-fusion.
    rrf_k:
        RRF damping constant.
    """

    def __init__(
        self,
        classifier: LanguageClassifier,
        retriever: DenseRetriever,
        translator: Translator | None = None,
        top_k: int = 5,
        per_query_k: int | None = None,
        threshold: float = 0.35,
        rrf_k: int = 60,
    ) -> None:
        self._classifier = classifier
        self._retriever = retriever
        self._translator: Translator = translator or IdentityTranslator()
        self._top_k = top_k
        self._per_query_k = per_query_k if per_query_k is not None else 2 * top_k
        self._threshold = threshold
        self._rrf_k = rrf_k

    def route(self, query: str) -> RoutedResult:
        """Classify, retrieve, threshold, (fuse), and truncate."""
        lang: LanguageResult = self._classifier.classify(query)
        logger.info(
            "Routing query (lang=%s, conf=%.2f): %s",
            lang.language, lang.confidence, query[:80],
        )

        if lang.language in ("hi", "en", "other"):
            return self._direct(query, lang)
        if lang.language == "hinglish":
            return self._dual(query, lang)

        # Unknown label — fall through to direct as the safe default.
        logger.warning("Unknown language label %r; falling back to direct", lang.language)
        return self._direct(query, lang)

    # ------------------------------------------------------------------ #
    # Strategies
    # ------------------------------------------------------------------ #

    def _direct(self, query: str, lang: LanguageResult) -> RoutedResult:
        hits = self._retriever.retrieve(query, k=self._per_query_k)
        hits = apply_threshold(hits, self._threshold)
        hits = hits[: self._top_k]
        return RoutedResult(
            results=hits,
            language=lang.language,
            language_confidence=lang.confidence,
            strategy="direct",
            queries_used=[query],
        )

    def _dual(self, query: str, lang: LanguageResult) -> RoutedResult:
        q_hi = self._translator.translate_to(query, "hi")
        q_en = self._translator.translate_to(query, "en")
        queries_used = [q_hi, q_en]

        hits_hi = self._retriever.retrieve(q_hi, k=self._per_query_k)
        hits_en = self._retriever.retrieve(q_en, k=self._per_query_k)

        # Threshold each list BEFORE fusion — fused RRF scores are not
        # cosine-comparable.
        hits_hi = apply_threshold(hits_hi, self._threshold)
        hits_en = apply_threshold(hits_en, self._threshold)

        fused = reciprocal_rank_fusion(
            [hits_hi, hits_en],
            k=self._rrf_k,
            top_k=self._top_k,
        )
        return RoutedResult(
            results=fused,
            language=lang.language,
            language_confidence=lang.confidence,
            strategy="dual",
            queries_used=queries_used,
        )
