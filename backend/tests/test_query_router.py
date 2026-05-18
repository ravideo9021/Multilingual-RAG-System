"""Tests for :class:`app.retrieval.query_router.QueryRouter`.

The router is pure glue, so we use stub objects for the classifier,
retriever, and translator. This gives us full control over what each
component returns and lets us assert on exactly which retrieval passes
happened.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.retrieval.language_classifier import LanguageResult
from app.retrieval.query_router import (
    IdentityTranslator,
    QueryRouter,
    RoutedResult,
    Translator,
)


# ---------------------------------------------------------------------- #
# Stubs
# ---------------------------------------------------------------------- #


class _StubClassifier:
    def __init__(self, result: LanguageResult):
        self._result = result

    def classify(self, text: str) -> LanguageResult:
        return self._result


class _StubRetriever:
    """Records every retrieve() call, returns canned results keyed by query."""

    def __init__(self, canned: dict[str, list[dict[str, Any]]] | None = None):
        self._canned = canned or {}
        self.calls: list[tuple[str, int]] = []

    def retrieve(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        self.calls.append((query, k))
        return list(self._canned.get(query, []))


class _RecordingTranslator:
    def __init__(self):
        self.calls: list[tuple[str, str]] = []

    def translate_to(self, text: str, target_lang: str) -> str:
        self.calls.append((text, target_lang))
        return f"[{target_lang}]{text}"


def _lang(label: str, conf: float = 0.9) -> LanguageResult:
    return LanguageResult(
        language=label,
        confidence=conf,
        devanagari_ratio=0.0,
        latin_ratio=0.0,
    )


# ---------------------------------------------------------------------- #
# Identity translator
# ---------------------------------------------------------------------- #


class TestIdentityTranslator:
    def test_returns_input_unchanged(self):
        t = IdentityTranslator()
        assert t.translate_to("hello", "hi") == "hello"
        assert t.translate_to("नमस्ते", "en") == "नमस्ते"

    def test_satisfies_translator_protocol(self):
        assert isinstance(IdentityTranslator(), Translator)


# ---------------------------------------------------------------------- #
# Direct strategy (hi / en / other)
# ---------------------------------------------------------------------- #


class TestDirectStrategy:
    def test_english_takes_direct_path(self):
        retriever = _StubRetriever({
            "what is India?": [
                {"id": 1, "score": 0.9, "text": "A"},
                {"id": 2, "score": 0.8, "text": "B"},
            ]
        })
        translator = _RecordingTranslator()
        router = QueryRouter(
            classifier=_StubClassifier(_lang("en")),
            retriever=retriever,
            translator=translator,
            top_k=5,
            threshold=0.0,
        )
        routed = router.route("what is India?")
        assert routed.strategy == "direct"
        assert routed.language == "en"
        assert routed.queries_used == ["what is India?"]
        assert len(retriever.calls) == 1
        # Translator is NEVER called on the direct path.
        assert translator.calls == []
        assert len(routed.results) == 2

    def test_hindi_takes_direct_path(self):
        retriever = _StubRetriever({
            "भारत क्या है?": [{"id": 1, "score": 0.9, "text": "A"}],
        })
        router = QueryRouter(
            classifier=_StubClassifier(_lang("hi")),
            retriever=retriever,
            translator=IdentityTranslator(),
            threshold=0.0,
        )
        routed = router.route("भारत क्या है?")
        assert routed.strategy == "direct"
        assert routed.language == "hi"

    def test_other_language_takes_direct_path(self):
        retriever = _StubRetriever({"hola": []})
        router = QueryRouter(
            classifier=_StubClassifier(_lang("other", 0.4)),
            retriever=retriever,
            translator=IdentityTranslator(),
        )
        routed = router.route("hola")
        assert routed.strategy == "direct"
        assert routed.language == "other"

    def test_direct_applies_threshold(self):
        retriever = _StubRetriever({
            "q": [
                {"id": 1, "score": 0.9},
                {"id": 2, "score": 0.4},  # below 0.5
                {"id": 3, "score": 0.6},
            ]
        })
        router = QueryRouter(
            classifier=_StubClassifier(_lang("en")),
            retriever=retriever,
            threshold=0.5,
        )
        routed = router.route("q")
        assert [h["id"] for h in routed.results] == [1, 3]

    def test_direct_truncates_to_top_k(self):
        retriever = _StubRetriever({
            "q": [{"id": i, "score": 0.9 - i * 0.01} for i in range(10)]
        })
        router = QueryRouter(
            classifier=_StubClassifier(_lang("en")),
            retriever=retriever,
            top_k=3,
            threshold=0.0,
        )
        routed = router.route("q")
        assert len(routed.results) == 3


# ---------------------------------------------------------------------- #
# Dual strategy (hinglish)
# ---------------------------------------------------------------------- #


class TestDualStrategy:
    def test_hinglish_issues_dual_queries(self):
        translator = _RecordingTranslator()
        retriever = _StubRetriever({
            "[hi]kya hai": [{"id": 1, "score": 0.9, "text": "हिंदी"}],
            "[en]kya hai": [{"id": 2, "score": 0.85, "text": "English"}],
        })
        router = QueryRouter(
            classifier=_StubClassifier(_lang("hinglish", 0.6)),
            retriever=retriever,
            translator=translator,
            threshold=0.0,
        )
        routed = router.route("kya hai")
        assert routed.strategy == "dual"
        assert routed.language == "hinglish"
        # Translator called once per target language.
        assert ("kya hai", "hi") in translator.calls
        assert ("kya hai", "en") in translator.calls
        # Two retrieval calls happened.
        queries_searched = [c[0] for c in retriever.calls]
        assert "[hi]kya hai" in queries_searched
        assert "[en]kya hai" in queries_searched
        # Both results present after RRF fusion.
        result_ids = {h["id"] for h in routed.results}
        assert result_ids == {1, 2}

    def test_dual_fuses_shared_documents(self):
        """A doc appearing in both language results should outrank singletons."""
        translator = IdentityTranslator()  # identity: both queries = original
        retriever = _StubRetriever({
            "kya hai": [
                {"id": 1, "score": 0.9, "text": "shared"},
                {"id": 2, "score": 0.8, "text": "hi-only"},
                {"id": 3, "score": 0.7, "text": "shared"},  # same id? no, use 1
            ],
        })
        # Reshape: two different lists, shared id=1.
        retriever = _StubRetriever({
            "kya hai": [
                {"id": 1, "score": 0.9, "text": "shared"},
                {"id": 2, "score": 0.8, "text": "only-A"},
            ]
        })
        # With identity translator both passes return the SAME list, so
        # id=1 gets 2 * 1/61 while id=2 gets 2 * 1/62 — still sorted correctly.
        router = QueryRouter(
            classifier=_StubClassifier(_lang("hinglish")),
            retriever=retriever,
            translator=translator,
            threshold=0.0,
        )
        routed = router.route("kya hai")
        assert routed.results[0]["id"] == 1
        # Score is fused (not 0.9).
        assert routed.results[0]["score"] == pytest.approx(2 / 61)

    def test_dual_applies_threshold_pre_fusion(self):
        """Low-scoring pre-fusion hits are dropped before RRF."""
        retriever = _StubRetriever({
            "[hi]q": [
                {"id": 1, "score": 0.9},
                {"id": 2, "score": 0.3},  # below 0.5
            ],
            "[en]q": [
                {"id": 3, "score": 0.6},
                {"id": 4, "score": 0.2},  # below 0.5
            ],
        })
        router = QueryRouter(
            classifier=_StubClassifier(_lang("hinglish")),
            retriever=retriever,
            translator=_RecordingTranslator(),
            threshold=0.5,
        )
        routed = router.route("q")
        ids = {h["id"] for h in routed.results}
        assert ids == {1, 3}
        assert 2 not in ids and 4 not in ids

    def test_dual_respects_top_k(self):
        # Both passes return 5 disjoint items each → 10 total.
        hi_hits = [{"id": i, "score": 0.9} for i in range(5)]
        en_hits = [{"id": i + 100, "score": 0.9} for i in range(5)]
        retriever = _StubRetriever({"[hi]q": hi_hits, "[en]q": en_hits})
        router = QueryRouter(
            classifier=_StubClassifier(_lang("hinglish")),
            retriever=retriever,
            translator=_RecordingTranslator(),
            top_k=3,
            threshold=0.0,
        )
        routed = router.route("q")
        assert len(routed.results) == 3

    def test_dual_empty_both_lists(self):
        retriever = _StubRetriever({})  # returns [] for any query
        router = QueryRouter(
            classifier=_StubClassifier(_lang("hinglish")),
            retriever=retriever,
            translator=_RecordingTranslator(),
            threshold=0.0,
        )
        routed = router.route("q")
        assert routed.results == []
        assert routed.strategy == "dual"


# ---------------------------------------------------------------------- #
# Defaults & wiring
# ---------------------------------------------------------------------- #


class TestDefaults:
    def test_default_translator_is_identity(self):
        retriever = _StubRetriever({"q": []})
        router = QueryRouter(
            classifier=_StubClassifier(_lang("hinglish")),
            retriever=retriever,
        )
        # Doesn't crash — and issues dual queries with identity translation.
        routed = router.route("q")
        assert routed.strategy == "dual"
        # Both translated queries equal the original under identity.
        assert routed.queries_used == ["q", "q"]

    def test_per_query_k_defaults_to_twice_top_k(self):
        retriever = _StubRetriever({"q": []})
        router = QueryRouter(
            classifier=_StubClassifier(_lang("en")),
            retriever=retriever,
            top_k=4,
        )
        router.route("q")
        assert retriever.calls == [("q", 8)]

    def test_per_query_k_override_honored(self):
        retriever = _StubRetriever({"q": []})
        router = QueryRouter(
            classifier=_StubClassifier(_lang("en")),
            retriever=retriever,
            top_k=5,
            per_query_k=20,
        )
        router.route("q")
        assert retriever.calls == [("q", 20)]


class TestRoutedResultDataclass:
    def test_fields(self):
        r = RoutedResult(
            results=[{"id": 1, "score": 0.9}],
            language="en",
            language_confidence=0.95,
            strategy="direct",
            queries_used=["hello"],
        )
        assert r.language == "en"
        assert r.strategy == "direct"
        assert r.queries_used == ["hello"]
