"""Tests for :class:`app.retrieval.language_classifier.LanguageClassifier`.

We never load the real fastText model (~125 MB). Instead, each test that
needs fastText substitutes a :class:`_StubFastText` via attribute
assignment on the classifier instance.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.retrieval.language_classifier import (
    LanguageClassifier,
    LanguageResult,
    _script_counts,
)


# ---------------------------------------------------------------------- #
# Stub fastText
# ---------------------------------------------------------------------- #


class _StubFastText:
    """Minimal stand-in for a loaded fastText model.

    Returns ``(label, confidence)`` from a mapping of text substrings
    (longest match wins), or a configured default.
    """

    def __init__(self, mapping: dict[str, tuple[str, float]], default=("en", 0.9)):
        self._mapping = mapping
        self._default = default

    def predict(self, text: str, k: int = 1):
        # Return the first substring match; else the default.
        for needle, (label, conf) in sorted(
            self._mapping.items(), key=lambda kv: -len(kv[0])
        ):
            if needle in text:
                return ([f"__label__{label}"], [conf])
        label, conf = self._default
        return ([f"__label__{label}"], [conf])


def _make_classifier(stub: _StubFastText | None = None) -> LanguageClassifier:
    """Build a classifier and short-circuit the model load."""
    clf = LanguageClassifier(
        model_path=Path("/nonexistent"),  # won't be used — we stub
        script_dominance=0.7,
        fasttext_confidence=0.6,
    )
    clf._model = stub  # bypass _ensure_loaded
    return clf


# ---------------------------------------------------------------------- #
# Script counting helper
# ---------------------------------------------------------------------- #


class TestScriptCounts:
    def test_pure_devanagari(self):
        dev, lat, total = _script_counts("नमस्ते")
        assert dev == 6  # 6 Devanagari characters (including vowel signs)
        assert lat == 0
        assert total == 6

    def test_pure_latin(self):
        dev, lat, total = _script_counts("hello")
        assert dev == 0
        assert lat == 5
        assert total == 5

    def test_mixed(self):
        dev, lat, total = _script_counts("hi भारत")
        assert dev == 4  # भ, ा, र, त
        assert lat == 2
        assert total == 6

    def test_ignores_punctuation_and_digits(self):
        dev, lat, total = _script_counts("hello 123 !@#")
        assert dev == 0
        assert lat == 5
        assert total == 5

    def test_empty(self):
        assert _script_counts("") == (0, 0, 0)

    def test_counts_other_letters_in_total_only(self):
        # Cyrillic 'привет' → 6 letters, neither Devanagari nor Latin.
        dev, lat, total = _script_counts("привет")
        assert dev == 0
        assert lat == 0
        assert total == 6


# ---------------------------------------------------------------------- #
# Classification rules
# ---------------------------------------------------------------------- #


class TestHindiDominant:
    def test_pure_hindi_returns_hi(self):
        clf = _make_classifier()
        result = clf.classify("भारत एक देश है।")
        assert result.language == "hi"
        assert result.devanagari_ratio > 0.9
        # Devanagari-dominant rule short-circuits before fastText.
        assert result.fasttext_label is None

    def test_real_hindi_wikipedia_opening(self):
        clf = _make_classifier()
        text = "भारत एक प्रायद्वीपीय देश है जो दक्षिण एशिया में स्थित है।"
        result = clf.classify(text)
        assert result.language == "hi"


class TestMixedScripts:
    def test_hi_and_latin_present_returns_hinglish(self):
        clf = _make_classifier()
        result = clf.classify("भारत is a country in South Asia")
        # Both scripts present → hinglish by rule 2.
        assert result.language == "hinglish"
        assert result.devanagari_ratio > 0
        assert result.latin_ratio > 0

    def test_mostly_english_with_one_hindi_word(self):
        clf = _make_classifier()
        result = clf.classify("I live in दिल्ली city")
        # Any Devanagari + any Latin → hinglish.
        assert result.language == "hinglish"


class TestEnglishDominant:
    def test_high_confidence_english_returns_en(self):
        stub = _StubFastText({}, default=("en", 0.95))
        clf = _make_classifier(stub)
        result = clf.classify("The quick brown fox jumps over the lazy dog")
        assert result.language == "en"
        assert result.fasttext_label == "en"
        assert result.confidence == pytest.approx(0.95)

    def test_low_confidence_english_returns_hinglish(self):
        """Romanized Hindi often trips fastText into low-confidence English."""
        stub = _StubFastText({}, default=("en", 0.45))
        clf = _make_classifier(stub)
        result = clf.classify("mera naam ravi hai aur main dilli mein rehta hoon")
        assert result.language == "hinglish"
        assert result.fasttext_label == "en"

    def test_latin_but_fasttext_says_hindi_returns_hinglish(self):
        """fastText sometimes correctly identifies romanized Hindi as 'hi'."""
        stub = _StubFastText({}, default=("hi", 0.8))
        clf = _make_classifier(stub)
        result = clf.classify("kya tum theek ho dost")
        # Latin-dominant + fastText not confident English → hinglish.
        assert result.language == "hinglish"
        assert result.fasttext_label == "hi"


class TestOther:
    def test_pure_cjk_returns_other(self):
        stub = _StubFastText({}, default=("zh", 0.95))
        clf = _make_classifier(stub)
        result = clf.classify("你好世界")  # "Hello world" in Chinese
        # No Devanagari, no Latin → falls through to "other".
        assert result.language == "other"

    def test_empty_string_returns_other(self):
        clf = _make_classifier()
        result = clf.classify("")
        assert result.language == "other"
        assert result.confidence == 0.0

    def test_whitespace_only_returns_other(self):
        clf = _make_classifier()
        result = clf.classify("   \n\t  ")
        assert result.language == "other"


class TestThresholdConfiguration:
    def test_lower_script_dominance_flips_borderline_mix_to_hi(self):
        """Rule 1 (Devanagari-dominant) evaluates BEFORE rule 2 (mix → hinglish),
        so relaxing the dominance threshold pulls borderline-Devanagari text
        out of ``hinglish`` and into ``hi``."""
        # 'भारतम' = 5 Devanagari chars; 'abcd' = 4 Latin → 5/9 ≈ 0.556 Devanagari.
        text = "भारतम abcd"

        # Default (0.7 dominance): 0.556 < 0.7 → rule 2 fires → hinglish.
        default_clf = _make_classifier(_StubFastText({}))
        assert default_clf.classify(text).language == "hinglish"

        # Relaxed (0.5 dominance): 0.556 ≥ 0.5 → rule 1 fires → hi.
        # This is the intended knob: loosening `script_dominance` means
        # "trust smaller Devanagari majorities as Hindi."
        relaxed = LanguageClassifier(
            model_path=Path("/nonexistent"),
            script_dominance=0.5,
            fasttext_confidence=0.6,
        )
        relaxed._model = _StubFastText({})
        assert relaxed.classify(text).language == "hi"

    def test_higher_fasttext_threshold_pushes_borderline_to_hinglish(self):
        """Raising the English-confidence bar means more Latin text falls to hinglish."""
        # Stub returns en @ 0.7.
        stub = _StubFastText({}, default=("en", 0.7))
        lenient = LanguageClassifier(
            model_path=Path("/nonexistent"),
            script_dominance=0.7,
            fasttext_confidence=0.6,
        )
        lenient._model = stub
        strict = LanguageClassifier(
            model_path=Path("/nonexistent"),
            script_dominance=0.7,
            fasttext_confidence=0.8,
        )
        strict._model = stub

        text = "hello how are you today"
        assert lenient.classify(text).language == "en"
        assert strict.classify(text).language == "hinglish"


class TestModelLoad:
    def test_missing_model_file_raises_clear_error(self, tmp_path):
        clf = LanguageClassifier(model_path=tmp_path / "does_not_exist.bin")
        with pytest.raises(FileNotFoundError, match="fastText.*download"):
            # Only triggers when _ensure_loaded runs — i.e., when
            # fastText is actually consulted. Force that by feeding
            # Latin-dominant text.
            clf.classify("hello world how are you")

    def test_hindi_only_text_does_not_load_model(self, tmp_path):
        """Devanagari-dominant shortcut must not trigger the model load."""
        clf = LanguageClassifier(model_path=tmp_path / "does_not_exist.bin")
        # Should not raise — the Devanagari-dominant branch returns early.
        result = clf.classify("भारत एक देश है")
        assert result.language == "hi"


class TestLanguageResultDataclass:
    def test_is_frozen(self):
        result = LanguageResult(
            language="en",
            confidence=0.9,
            devanagari_ratio=0.0,
            latin_ratio=1.0,
        )
        with pytest.raises(Exception):
            result.language = "hi"  # type: ignore[misc]

    def test_optional_fasttext_fields_default_none(self):
        result = LanguageResult(
            language="hi", confidence=0.95, devanagari_ratio=1.0, latin_ratio=0.0
        )
        assert result.fasttext_label is None
        assert result.fasttext_confidence is None
