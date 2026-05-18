"""Language classification for queries and chunks.

Combines two signals:

1. **fastText lid.176** — Facebook's compact language-ID model (~125 MB).
   Trained on 176 languages. Good on longer text in native scripts; less
   reliable on short / mixed / romanized input.

2. **Unicode script ratio** — simple codepoint counting (Devanagari vs Latin).
   This is what catches *Hinglish* (Hindi written in Latin script) which
   fastText typically classifies as English.

Combined label space:

* ``"hi"``       — native Devanagari Hindi
* ``"en"``       — English
* ``"hinglish"`` — romanized Hindi, code-mixed Hindi+English, or script-mixed
* ``"other"``    — anything else (e.g., French, Chinese)

Detection rules (all thresholds come from :mod:`app.config`):

* If Devanagari ratio ≥ ``lang_script_dominance`` (default 0.7) → ``"hi"``.
* Else if Devanagari ratio > 0 and Latin ratio > 0 (both scripts present) →
  ``"hinglish"`` — script-mixed text is Hinglish in this corpus.
* Else if Latin ratio ≥ ``lang_script_dominance`` (default 0.7):
  fastText decides. If fastText says ``"en"`` with confidence ≥
  ``lang_fasttext_confidence`` (default 0.6) → ``"en"``. Otherwise we treat
  low-confidence English as likely romanized Hindi → ``"hinglish"``.
* Else (not enough Latin or Devanagari content, e.g., pure CJK) → ``"other"``.

The fastText model is loaded lazily on first :pymeth:`classify` call; the
constructor is cheap so this class is safe to instantiate at import time.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)


# Unicode code-point ranges we recognize.
#
# Devanagari: U+0900-U+097F (main block) + U+A8E0-U+A8FF (Devanagari Extended)
# Latin: basic A-Z / a-z only. Latin-1 accented letters are ignored — they
# don't matter for hi/en/hinglish discrimination.


def _script_counts(text: str) -> tuple[int, int, int]:
    """Count Devanagari, Latin, and total letter-like characters in ``text``.

    Returns ``(devanagari_count, latin_count, letter_count)``.
    Whitespace, digits, and punctuation are excluded from the letter count so
    a string like ``"123 !@#"`` doesn't count as "scripted" text at all.
    """
    dev = 0
    lat = 0
    letters = 0
    for ch in text:
        cp = ord(ch)
        if 0x0900 <= cp <= 0x097F or 0xA8E0 <= cp <= 0xA8FF:
            dev += 1
            letters += 1
        elif (0x0041 <= cp <= 0x005A) or (0x0061 <= cp <= 0x007A):
            lat += 1
            letters += 1
        elif ch.isalpha():
            # Non-Latin, non-Devanagari letter (e.g., Cyrillic, CJK, Arabic).
            letters += 1
    return dev, lat, letters


@dataclass(frozen=True)
class LanguageResult:
    """Outcome of classifying one piece of text."""

    language: str  # "hi" | "en" | "hinglish" | "other"
    confidence: float  # 0.0 .. 1.0
    devanagari_ratio: float
    latin_ratio: float
    # The raw fastText top label (e.g., "en", "hi", "ur") and its probability.
    # Useful for debugging / tuning. None if fastText wasn't consulted
    # (empty input, or the Devanagari-dominant shortcut fired first).
    fasttext_label: str | None = None
    fasttext_confidence: float | None = None


class LanguageClassifier:
    """Classify text into ``hi`` / ``en`` / ``hinglish`` / ``other``.

    Parameters
    ----------
    model_path:
        Path to fastText's ``lid.176.bin``. Default comes from
        :pyattr:`Settings.fasttext_model_path`. Download via
        ``scripts/download_models.sh``.
    script_dominance:
        Minimum script ratio (0-1) to be called "dominant". Default 0.7.
    fasttext_confidence:
        Minimum fastText confidence to trust its English verdict on
        Latin-dominant text. Below this, Latin-only text is labeled
        Hinglish (likely romanized Hindi). Default 0.6.
    """

    def __init__(
        self,
        model_path: str | Path | None = None,
        script_dominance: float | None = None,
        fasttext_confidence: float | None = None,
        settings: "Settings | None" = None,
    ) -> None:
        if settings is None:
            from app.config import settings as _settings

            settings = _settings

        self._model_path = Path(model_path) if model_path else Path(settings.fasttext_model_path)
        self._script_dominance = (
            script_dominance if script_dominance is not None else settings.lang_script_dominance
        )
        self._fasttext_confidence = (
            fasttext_confidence
            if fasttext_confidence is not None
            else settings.lang_fasttext_confidence
        )
        self._model = None  # lazy

    # ------------------------------------------------------------------ #
    # Lazy model load
    # ------------------------------------------------------------------ #

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        if not self._model_path.exists():
            raise FileNotFoundError(
                f"fastText language ID model not found at {self._model_path}. "
                f"Download it with: bash scripts/download_models.sh"
            )
        try:
            import fasttext
        except ImportError as exc:
            raise ImportError(
                "fasttext is not installed. Install with "
                "`uv sync` (it's pinned in pyproject.toml)."
            ) from exc

        logger.info("Loading fastText language ID model from %s", self._model_path)
        # fasttext prints a deprecation warning to stderr on load; not our problem.
        self._model = fasttext.load_model(str(self._model_path))

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def classify(self, text: str) -> LanguageResult:
        """Classify a single string."""
        text = (text or "").strip()
        if not text:
            return LanguageResult(
                language="other",
                confidence=0.0,
                devanagari_ratio=0.0,
                latin_ratio=0.0,
            )

        dev_n, lat_n, total = _script_counts(text)
        dev_ratio = dev_n / total if total else 0.0
        lat_ratio = lat_n / total if total else 0.0

        # Rule 1 — Devanagari-dominant: definitely Hindi. Skip fastText.
        if dev_ratio >= self._script_dominance:
            return LanguageResult(
                language="hi",
                confidence=dev_ratio,
                devanagari_ratio=dev_ratio,
                latin_ratio=lat_ratio,
            )

        # Rule 2 — both scripts present at non-trivial levels: Hinglish.
        # (Covers "भारत is India" style mixing.)
        if dev_ratio > 0 and lat_ratio > 0:
            return LanguageResult(
                language="hinglish",
                confidence=max(dev_ratio, lat_ratio),
                devanagari_ratio=dev_ratio,
                latin_ratio=lat_ratio,
            )

        # Rule 3 — Latin-dominant: consult fastText to disambiguate
        # English vs romanized Hindi.
        if lat_ratio >= self._script_dominance:
            ft_label, ft_conf = self._fasttext_predict(text)
            if ft_label == "en" and ft_conf >= self._fasttext_confidence:
                return LanguageResult(
                    language="en",
                    confidence=ft_conf,
                    devanagari_ratio=dev_ratio,
                    latin_ratio=lat_ratio,
                    fasttext_label=ft_label,
                    fasttext_confidence=ft_conf,
                )
            # Low-confidence English on Latin-only text → likely Hinglish.
            # This is a conservative call: on purely English short queries
            # fastText sometimes returns <0.6 confidence, which will
            # mislabel them. The downstream router handles this by
            # retrieving against both languages anyway, so the cost of
            # a false Hinglish label is mild.
            return LanguageResult(
                language="hinglish",
                confidence=ft_conf,
                devanagari_ratio=dev_ratio,
                latin_ratio=lat_ratio,
                fasttext_label=ft_label,
                fasttext_confidence=ft_conf,
            )

        # Rule 4 — neither script dominant and not mixed hi+en: other.
        ft_label, ft_conf = self._fasttext_predict(text)
        return LanguageResult(
            language="other",
            confidence=ft_conf,
            devanagari_ratio=dev_ratio,
            latin_ratio=lat_ratio,
            fasttext_label=ft_label,
            fasttext_confidence=ft_conf,
        )

    def _fasttext_predict(self, text: str) -> tuple[str, float]:
        """Predict with fastText; return ``(iso_code, confidence)``."""
        self._ensure_loaded()
        # fastText chokes on newlines in input — replace with spaces.
        cleaned = text.replace("\n", " ")
        labels, probs = self._model.predict(cleaned, k=1)
        # Label format is "__label__en"; strip the prefix.
        label = labels[0].replace("__label__", "")
        return label, float(probs[0])
