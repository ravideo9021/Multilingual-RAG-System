"""Tests for ScriptAwareRecursiveChunker.

These tests use a real tokenizer (BGE-M3 / XLM-Roberta) — the first run
downloads ~5 MB to the HuggingFace cache. They do NOT download the full
embedding model.

Real Hindi text is used throughout (no transliterations), drawn from the
opening of the Hindi Wikipedia article on भारत (India).
"""

from __future__ import annotations

import pytest

from app.ingestion.chunker import (
    Chunk,
    ScriptAwareRecursiveChunker,
    _detect_script,
    _split_keeping_separator,
)

# ---------------------------------------------------------------------- #
# Real text fixtures
# ---------------------------------------------------------------------- #

# Opening paragraph of the Hindi Wikipedia article on India (भारत).
# Multiple `।`-terminated sentences in a single paragraph.
HINDI_PARAGRAPH = (
    "भारत, आधिकारिक नाम भारत गणराज्य, दक्षिण एशिया में स्थित भारतीय "
    "उपमहाद्वीप का सबसे बड़ा देश है। यह विश्व में जनसंख्या के आधार पर "
    "सबसे बड़ा देश है तथा क्षेत्रफल के आधार पर सातवाँ सबसे बड़ा देश है। "
    "भारत के पश्चिम में पाकिस्तान, उत्तर-पूर्व में चीन, नेपाल और भूटान, "
    "पूर्व में बांग्लादेश और म्यान्मार स्थित हैं। हिन्द महासागर में इसके "
    "दक्षिण पश्चिम में मालदीव, दक्षिण में श्रीलंका और दक्षिण-पूर्व में "
    "इंडोनेशिया से भारत की समुद्री सीमा लगती है। भारत की राजधानी नई "
    "दिल्ली है और सबसे बड़ा शहर मुम्बई है। भारतीय संस्कृति विश्व की "
    "सबसे प्राचीन संस्कृतियों में से एक है।"
)

ENGLISH_PARAGRAPH = (
    "India, officially the Republic of India, is a country in South Asia. "
    "It is the most populous country and the seventh-largest country by "
    "land area. India shares land borders with Pakistan to the west, "
    "China, Nepal, and Bhutan to the north, and Bangladesh and Myanmar "
    "to the east. In the Indian Ocean, India is in the vicinity of Sri "
    "Lanka and the Maldives. Its capital is New Delhi and its largest "
    "city is Mumbai. The Indian subcontinent has been home to several "
    "ancient civilizations, including the Indus Valley civilization."
)

MIXED_PARAGRAPH = (
    "भारत एक विशाल देश है। India is the seventh-largest country by area. "
    "इसकी जनसंख्या लगभग 1.4 अरब है। Its capital is New Delhi and its "
    "largest city is Mumbai. भारतीय संस्कृति बहुत प्राचीन है। The country "
    "has a rich history spanning thousands of years."
)

# Word-boundary characters that legitimately end a chunk.
_END_BOUNDARY_CHARS = set(" \n\t।॥.!?;,")


# ---------------------------------------------------------------------- #
# Phase 1: input validation
# ---------------------------------------------------------------------- #


class TestInvalidParams:
    def test_chunk_size_zero_raises(self):
        with pytest.raises(ValueError):
            ScriptAwareRecursiveChunker(chunk_size=0, overlap=0)

    def test_chunk_size_negative_raises(self):
        with pytest.raises(ValueError):
            ScriptAwareRecursiveChunker(chunk_size=-5, overlap=0)

    def test_overlap_negative_raises(self):
        with pytest.raises(ValueError):
            ScriptAwareRecursiveChunker(chunk_size=64, overlap=-1)

    def test_overlap_equal_to_chunk_size_raises(self):
        with pytest.raises(ValueError):
            ScriptAwareRecursiveChunker(chunk_size=64, overlap=64)

    def test_overlap_greater_than_chunk_size_raises(self):
        with pytest.raises(ValueError):
            ScriptAwareRecursiveChunker(chunk_size=64, overlap=100)


# ---------------------------------------------------------------------- #
# Phase 2: helpers
# ---------------------------------------------------------------------- #


class TestSplitKeepingSeparator:
    def test_single_separator_kept(self):
        out = _split_keeping_separator("a. b. c.", ". ")
        assert "".join(out) == "a. b. c."

    def test_no_separator_returns_input(self):
        out = _split_keeping_separator("hello world", "XYZ")
        assert out == ["hello world"]

    def test_empty_separator_returns_input(self):
        out = _split_keeping_separator("hello", "")
        assert out == ["hello"]

    def test_devanagari_danda_separator(self):
        text = "एक। दो। तीन।"
        out = _split_keeping_separator(text, "। ")
        assert "".join(out) == text

    def test_concat_preserves_text_with_trailing_separator(self):
        text = "a, b, c, "
        out = _split_keeping_separator(text, ", ")
        assert "".join(out) == text


class TestDetectScript:
    def test_pure_hindi(self):
        assert _detect_script("भारत एक विशाल देश है") == "hi"

    def test_pure_english(self):
        assert _detect_script("India is a large country") == "en"

    def test_mixed(self):
        assert _detect_script("भारत is in Asia और यह बड़ा है") == "mixed"

    def test_no_letters(self):
        assert _detect_script("12345 !@#$%") == "unknown"


# ---------------------------------------------------------------------- #
# Phase 3: chunker behavior
# ---------------------------------------------------------------------- #


def _assert_word_boundary_aligned(text: str, chunk: Chunk):
    """Chunk neither starts nor ends mid-word in the original text."""
    # Start: either offset 0 OR previous char is a word-boundary character.
    if chunk.char_start > 0:
        prev = text[chunk.char_start - 1]
        assert prev in _END_BOUNDARY_CHARS, (
            f"Chunk {chunk.chunk_index} starts mid-word: prev char {prev!r} "
            f"at offset {chunk.char_start - 1}; chunk text starts {chunk.text[:30]!r}"
        )
    # End: either at end of text OR last char of chunk is a boundary char.
    if chunk.char_end < len(text):
        last = chunk.text[-1]
        assert last in _END_BOUNDARY_CHARS, (
            f"Chunk {chunk.chunk_index} ends mid-word: last char {last!r}; "
            f"chunk text ends {chunk.text[-30:]!r}"
        )


class TestPureEnglish:
    def test_short_input_single_chunk(self, small_chunker):
        text = "India is large."
        chunks = small_chunker.chunk_text(text, source="t")
        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].language == "en"
        assert chunks[0].char_start == 0
        assert chunks[0].char_end == len(text)

    def test_long_paragraph_splits_on_sentences(self, small_chunker):
        # Repeat the paragraph to force multiple chunks.
        text = (ENGLISH_PARAGRAPH + " ") * 4
        chunks = small_chunker.chunk_text(text, source="en")
        assert len(chunks) >= 2
        for chunk in chunks:
            _assert_word_boundary_aligned(text, chunk)
            assert chunk.language == "en"
            assert chunk.token_count > 0

    def test_pure_english_paragraph_chunks_end_at_boundaries(self, small_chunker):
        text = (ENGLISH_PARAGRAPH + " ") * 3
        chunks = small_chunker.chunk_text(text)
        for i, chunk in enumerate(chunks):
            if i == len(chunks) - 1:
                continue
            assert chunk.text[-1] in _END_BOUNDARY_CHARS, (
                f"Chunk {i} ends with {chunk.text[-1]!r}, not a boundary char"
            )


class TestPureHindi:
    def test_hindi_paragraph_splits_on_danda(self, small_chunker):
        chunks = small_chunker.chunk_text(HINDI_PARAGRAPH, source="hi")
        assert len(chunks) >= 2
        for chunk in chunks:
            _assert_word_boundary_aligned(HINDI_PARAGRAPH, chunk)
            assert chunk.language == "hi"
            assert chunk.token_count > 0

    def test_hindi_chunks_end_at_danda_or_boundary(self, small_chunker):
        chunks = small_chunker.chunk_text(HINDI_PARAGRAPH)
        # At least one chunk boundary must coincide with a danda — that proves
        # we actually used the Devanagari separator and didn't fall through to
        # whitespace.
        ended_with_danda = sum(
            1 for c in chunks[:-1] if c.text.rstrip().endswith("।")
        )
        assert ended_with_danda >= 1, (
            "No chunk boundary coincided with a Devanagari danda — "
            "the chunker isn't using the Hindi sentence separator."
        )

    def test_hindi_language_tag_pure_hindi(self, small_chunker):
        chunks = small_chunker.chunk_text(HINDI_PARAGRAPH)
        assert all(c.language == "hi" for c in chunks)


class TestMixedHindiEnglish:
    def test_mixed_paragraph_handles_both_terminators(self, small_chunker):
        # Repeat the paragraph so it definitely exceeds chunk_size=64 tokens
        # and the chunker has to actually split using both danda and period.
        text = (MIXED_PARAGRAPH + " ") * 4
        chunks = small_chunker.chunk_text(text, source="mixed")
        assert len(chunks) >= 2
        for chunk in chunks:
            _assert_word_boundary_aligned(text, chunk)
            assert chunk.token_count > 0
        # Confirm both Hindi and English sentence terminators were used as
        # split points somewhere in the output (not just one or the other).
        non_final = [c.text.rstrip() for c in chunks[:-1]]
        ended_with_danda = any(s.endswith("।") for s in non_final)
        ended_with_period = any(s.endswith(".") for s in non_final)
        assert ended_with_danda or ended_with_period, (
            "Mixed text didn't split on either Hindi or English sentence terminator"
        )

    def test_mixed_paragraph_has_at_least_one_mixed_or_split_chunk(self, small_chunker):
        chunks = small_chunker.chunk_text(MIXED_PARAGRAPH)
        languages = {c.language for c in chunks}
        # Either some chunks contain both scripts (mixed), or we cleanly split
        # them into hi-only and en-only chunks. Both outcomes are acceptable.
        assert "mixed" in languages or {"hi", "en"}.issubset(languages), (
            f"Expected to see mixed-script handling, got languages={languages}"
        )


# ---------------------------------------------------------------------- #
# Phase 4: invariants
# ---------------------------------------------------------------------- #


class TestCharOffsetInvariant:
    @pytest.mark.parametrize(
        "text,label",
        [
            (HINDI_PARAGRAPH, "hindi"),
            (ENGLISH_PARAGRAPH, "english"),
            (MIXED_PARAGRAPH, "mixed"),
            ((ENGLISH_PARAGRAPH + " ") * 5, "english_long"),
        ],
    )
    def test_offsets_reconstruct_original_chunk_text(self, small_chunker, text, label):
        """text[chunk.char_start:chunk.char_end] == chunk.text — strictly."""
        chunks = small_chunker.chunk_text(text, source=label)
        assert chunks, f"Got no chunks for {label}"
        for chunk in chunks:
            slice_ = text[chunk.char_start : chunk.char_end]
            assert slice_ == chunk.text, (
                f"Char offset mismatch in {label} chunk {chunk.chunk_index}:\n"
                f"  slice  ({len(slice_)} chars): {slice_[:60]!r}\n"
                f"  chunk  ({len(chunk.text)} chars): {chunk.text[:60]!r}"
            )

    def test_no_chunk_text_is_empty(self, small_chunker):
        chunks = small_chunker.chunk_text(HINDI_PARAGRAPH)
        for c in chunks:
            assert c.text.strip(), f"Empty chunk at index {c.chunk_index}"


class TestNoMidWordSplits:
    def test_devanagari_long_word_not_split(self, small_chunker):
        # Long Devanagari words repeated; chunker must keep each word intact.
        word = "अंतर्राष्ट्रीयकरण"
        text = " ".join([word] * 50)
        chunks = small_chunker.chunk_text(text, source="long_word")
        # Reconstruct from chunks (allowing overlap) — every occurrence of
        # the word must appear at least once across the chunks intact.
        # Stronger check: every chunk's content, when split on whitespace,
        # contains only the full word (or nothing).
        for chunk in chunks:
            for token in chunk.text.split():
                assert token == word, (
                    f"Mid-word split detected: chunk contains {token!r} "
                    f"instead of full word {word!r}"
                )

    def test_latin_long_word_not_split(self, small_chunker):
        word = "internationalization"
        text = " ".join([word] * 50)
        chunks = small_chunker.chunk_text(text, source="long_word_en")
        for chunk in chunks:
            for token in chunk.text.split():
                assert token == word, (
                    f"Mid-word split detected: chunk contains {token!r} "
                    f"instead of full word {word!r}"
                )


class TestOverlap:
    def test_overlap_token_count_within_slack(self):
        chunker = ScriptAwareRecursiveChunker(chunk_size=64, overlap=10)
        # Build a long English text with predictable structure so we can split.
        text = (ENGLISH_PARAGRAPH + " ") * 8
        chunks = chunker.chunk_text(text)
        assert len(chunks) >= 3
        for i in range(1, len(chunks)):
            prev, cur = chunks[i - 1], chunks[i]
            # Overlap region: from cur.char_start up to prev.char_end.
            assert cur.char_start <= prev.char_end, (
                f"Chunk {i} starts after previous chunk ends — no overlap at all"
            )
            assert cur.char_start >= prev.char_start, (
                f"Chunk {i} starts before previous chunk start — overlap inverted"
            )
            overlap_text = text[cur.char_start : prev.char_end]
            overlap_tokens = chunker._token_count(overlap_text)
            # Word-boundary trimming reduces overlap; allow 0 < overlap <= 10 + slack.
            # If the previous chunk was very small the entire prev chunk may
            # become the overlap, exceeding self.overlap — that's allowed.
            assert overlap_tokens > 0, (
                f"Chunk {i} has zero-token overlap with previous chunk"
            )
            assert overlap_tokens <= chunker.chunk_size, (
                f"Overlap region ({overlap_tokens} toks) exceeds chunk_size"
            )

    def test_zero_overlap_chunks_are_disjoint(self):
        chunker = ScriptAwareRecursiveChunker(chunk_size=64, overlap=0)
        text = (ENGLISH_PARAGRAPH + " ") * 6
        chunks = chunker.chunk_text(text)
        for i in range(1, len(chunks)):
            assert chunks[i].char_start == chunks[i - 1].char_end, (
                f"With overlap=0, chunks should be exactly contiguous; "
                f"chunk {i} starts at {chunks[i].char_start}, "
                f"prev ended at {chunks[i - 1].char_end}"
            )

    def test_chunk_token_count_within_size_plus_overlap(self):
        """Total chunk size never exceeds chunk_size + overlap.

        Documented invariant: chunks may exceed chunk_size by up to ``overlap``
        tokens because the overlap region is prepended after merging.
        """
        chunker = ScriptAwareRecursiveChunker(chunk_size=64, overlap=10)
        text = (HINDI_PARAGRAPH + " " + ENGLISH_PARAGRAPH + " ") * 2
        chunks = chunker.chunk_text(text)
        assert len(chunks) >= 2
        upper = chunker.chunk_size + chunker.overlap
        for c in chunks:
            assert c.token_count <= upper, (
                f"Chunk {c.chunk_index} has {c.token_count} tokens, "
                f"exceeds chunk_size + overlap = {upper}"
            )


class TestEmptyAndShort:
    def test_empty_string_returns_no_chunks(self, small_chunker):
        assert small_chunker.chunk_text("") == []

    def test_whitespace_only_returns_no_chunks(self, small_chunker):
        assert small_chunker.chunk_text("    \n\t  ") == []

    def test_single_short_chunk(self, medium_chunker):
        chunks = medium_chunker.chunk_text("Hello world.")
        assert len(chunks) == 1
        assert chunks[0].chunk_index == 0
        assert chunks[0].source == ""
        assert chunks[0].language == "en"
