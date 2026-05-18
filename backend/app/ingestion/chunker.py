"""Script-aware recursive text chunker for Hindi + English mixed corpora.

The chunker splits text into approximately fixed-token chunks while respecting:

* **Devanagari sentence terminators** — danda ``।`` and double danda ``॥``
  ranked alongside Latin terminators (``.``, ``!``, ``?``).
* **Word boundaries** — chunks never start or end mid-word in either script
  except as a last-resort character split for pathological inputs.
* **True character offsets** — every chunk records the *exact* slice it came
  from in the original input, so ``original_text[chunk.char_start:chunk.char_end]``
  is byte-for-byte equal to ``chunk.text``.
* **Token-accurate sizing** — token counts come from the BGE-M3 (XLM-Roberta)
  tokenizer, not naive whitespace splitting, because Devanagari tokenization
  is non-trivial.

The class is *lazy*: the tokenizer is only loaded on first chunking call, so
importing the module is cheap.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from transformers import PreTrainedTokenizerBase

logger = logging.getLogger(__name__)

# Separator hierarchy: split on the first separator that produces sufficiently
# small pieces. Each separator is **kept attached to its preceding piece** so
# that re-concatenation reproduces the original text exactly. The empty string
# is the last-resort character split.
#
# Order matters: paragraph > line > Devanagari sentence > English sentence >
# weaker punctuation > word > character.
SEPARATORS: tuple[str, ...] = (
    "\n\n",  # paragraph
    "\n",  # line
    "। ",  # Devanagari danda + space (most common in well-typed Hindi)
    "॥ ",  # double danda + space
    "।",  # bare danda
    "॥",  # bare double danda
    ". ",  # English sentence
    "! ",
    "? ",
    "; ",
    ", ",
    " ",  # word
    "",  # character (last resort)
)

# Devanagari Unicode block: U+0900..U+097F
_DEVANAGARI_START = 0x0900
_DEVANAGARI_END = 0x097F


@dataclass(frozen=True)
class Chunk:
    """One chunk of text with its provenance and metadata."""

    text: str
    source: str
    chunk_index: int
    char_start: int
    char_end: int
    language: str  # "hi" | "en" | "mixed" | "unknown"
    token_count: int

    def to_dict(self) -> dict:
        return asdict(self)


def _detect_script(text: str) -> str:
    """Naive script detection by codepoint ratio.

    Returns ``"hi"`` if > 70% of letters are Devanagari, ``"en"`` if > 70% are
    Latin, ``"mixed"`` otherwise. ``"unknown"`` for text with no letters at all.

    The full fastText-based detector lives in :mod:`app.retrieval.language_classifier`
    (Chunk C). This is intentionally simple — it only labels chunks during
    ingestion so the retriever knows what's in the corpus.
    """
    devanagari = 0
    latin = 0
    for ch in text:
        cp = ord(ch)
        if _DEVANAGARI_START <= cp <= _DEVANAGARI_END:
            devanagari += 1
        elif ch.isascii() and ch.isalpha():
            latin += 1
    total = devanagari + latin
    if total == 0:
        return "unknown"
    if devanagari / total > 0.7:
        return "hi"
    if latin / total > 0.7:
        return "en"
    return "mixed"


class ScriptAwareRecursiveChunker:
    """Recursive chunker with Devanagari + Latin separator support.

    Parameters
    ----------
    chunk_size:
        Target maximum tokens of *new content* per chunk, before overlap is
        prepended. Must be ≥ 1. After overlap is added a chunk may be up to
        ``chunk_size + overlap`` tokens long, so callers should pick
        ``chunk_size`` such that ``chunk_size + overlap`` is safely below the
        embedding model's max input length (8192 for BGE-M3).
    overlap:
        Tokens of overlap between adjacent chunks. Must be ≥ 0 and < chunk_size.
    tokenizer_name:
        HuggingFace tokenizer ID used for token counting. Defaults to BGE-M3
        (XLM-Roberta), which is the same tokenizer used downstream for
        embedding, ensuring chunk sizes line up with the embedder's input limit.
    """

    # Class-level tokenizer cache, keyed by tokenizer_name. Different instances
    # with the same tokenizer share a single load. ``Any`` because we can't
    # import transformers at module level (it's a heavy import).
    _tokenizer_cache: ClassVar[dict[str, "PreTrainedTokenizerBase"]] = {}

    def __init__(
        self,
        chunk_size: int = 512,
        overlap: int = 80,
        tokenizer_name: str = "BAAI/bge-m3",
    ) -> None:
        if chunk_size < 1:
            raise ValueError(f"chunk_size must be >= 1, got {chunk_size}")
        if overlap < 0:
            raise ValueError(f"overlap must be >= 0, got {overlap}")
        if overlap >= chunk_size:
            raise ValueError(
                f"overlap ({overlap}) must be strictly less than chunk_size ({chunk_size})"
            )
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.tokenizer_name = tokenizer_name

    # ------------------------------------------------------------------ #
    # Tokenizer access
    # ------------------------------------------------------------------ #

    @property
    def tokenizer(self) -> "PreTrainedTokenizerBase":
        """Lazily load and cache the tokenizer."""
        cache = type(self)._tokenizer_cache
        tok = cache.get(self.tokenizer_name)
        if tok is None:
            logger.info("Loading tokenizer %s (first use)", self.tokenizer_name)
            from transformers import AutoTokenizer

            tok = AutoTokenizer.from_pretrained(self.tokenizer_name, use_fast=True)
            cache[self.tokenizer_name] = tok
        return tok

    def _token_count(self, text: str) -> int:
        if not text:
            return 0
        return len(self.tokenizer.encode(text, add_special_tokens=False))

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def chunk_text(self, text: str, source: str = "") -> list[Chunk]:
        """Split ``text`` into chunks.

        Returns an empty list for empty / whitespace-only input.
        """
        if not text or not text.strip():
            return []

        # Phase 1: recursive split into sub-pieces, each ≤ chunk_size tokens.
        pieces = self._split_recursive(text, start_offset=0, sep_index=0)

        # Phase 2: greedy merge into chunks, tracking (char_start, char_end).
        merged: list[tuple[int, int]] = self._merge_pieces(pieces)

        # Phase 3: extend each chunk's char_start backwards by `overlap` tokens
        # (word-boundary trimmed) to create the overlap region.
        if self.overlap > 0 and len(merged) > 1:
            merged = self._apply_overlap(text, merged)

        # Phase 4: build Chunk objects.
        chunks: list[Chunk] = []
        for i, (start, end) in enumerate(merged):
            chunk_text = text[start:end]
            chunks.append(
                Chunk(
                    text=chunk_text,
                    source=source,
                    chunk_index=i,
                    char_start=start,
                    char_end=end,
                    language=_detect_script(chunk_text),
                    token_count=self._token_count(chunk_text),
                )
            )
        return chunks

    # ------------------------------------------------------------------ #
    # Phase 1: recursive split
    # ------------------------------------------------------------------ #

    def _split_recursive(
        self, text: str, start_offset: int, sep_index: int
    ) -> list[tuple[str, int]]:
        """Return a list of ``(piece_text, piece_char_start_in_original)`` tuples.

        Every piece is ≤ ``chunk_size`` tokens. Concatenating all pieces
        reproduces ``text`` exactly (no character is dropped or duplicated).
        """
        if self._token_count(text) <= self.chunk_size:
            return [(text, start_offset)]

        # Hard char split is the last resort.
        if sep_index >= len(SEPARATORS):
            return self._hard_char_split(text, start_offset)

        sep = SEPARATORS[sep_index]
        if sep == "":
            return self._hard_char_split(text, start_offset)

        sub_pieces = _split_keeping_separator(text, sep)
        if len(sub_pieces) <= 1:
            # This separator didn't split anything; advance to the next.
            return self._split_recursive(text, start_offset, sep_index + 1)

        result: list[tuple[str, int]] = []
        cursor = 0
        for piece in sub_pieces:
            piece_start = start_offset + cursor
            if self._token_count(piece) > self.chunk_size:
                result.extend(self._split_recursive(piece, piece_start, sep_index + 1))
            else:
                result.append((piece, piece_start))
            cursor += len(piece)
        return result

    def _hard_char_split(self, text: str, start_offset: int) -> list[tuple[str, int]]:
        """Last-resort character-level split.

        Splits ``text`` into chunks of approximately ``chunk_size`` tokens by
        binary searching on character count. This may break mid-word, but is
        only reached for pathological inputs (e.g., a 10,000-character
        unbroken word).
        """
        if not text:
            return []
        if self._token_count(text) <= self.chunk_size:
            return [(text, start_offset)]

        # Estimate chars per token from this text and slice greedily.
        n_tokens = max(self._token_count(text), 1)
        chars_per_token = max(len(text) // n_tokens, 1)
        target_chars = max(self.chunk_size * chars_per_token, 1)

        result: list[tuple[str, int]] = []
        i = 0
        while i < len(text):
            j = min(i + target_chars, len(text))
            piece = text[i:j]
            # Shrink until under chunk_size tokens (could happen if estimate was off).
            while self._token_count(piece) > self.chunk_size and len(piece) > 1:
                j -= max((len(piece) - 1) // 8, 1)
                piece = text[i:j]
            result.append((piece, start_offset + i))
            i = j
        return result

    # ------------------------------------------------------------------ #
    # Phase 2: merge
    # ------------------------------------------------------------------ #

    def _merge_pieces(self, pieces: list[tuple[str, int]]) -> list[tuple[int, int]]:
        """Greedily merge adjacent pieces into chunks ≤ chunk_size tokens.

        Returns a list of ``(char_start, char_end)`` slices into the original
        text. Pieces are guaranteed contiguous in the original (no gaps), so
        the merged span is just (first.start, last.start + len(last.text)).
        """
        if not pieces:
            return []

        chunks: list[tuple[int, int]] = []
        cur_start: int | None = None
        cur_end: int = 0
        cur_text = ""

        for piece_text, piece_start in pieces:
            if cur_start is None:
                cur_start = piece_start
                cur_end = piece_start + len(piece_text)
                cur_text = piece_text
                continue

            candidate = cur_text + piece_text
            if self._token_count(candidate) <= self.chunk_size:
                # Extend current chunk.
                cur_text = candidate
                cur_end = piece_start + len(piece_text)
            else:
                # Emit current and start new.
                chunks.append((cur_start, cur_end))
                cur_start = piece_start
                cur_end = piece_start + len(piece_text)
                cur_text = piece_text

        if cur_start is not None:
            chunks.append((cur_start, cur_end))
        return chunks

    # ------------------------------------------------------------------ #
    # Phase 3: overlap
    # ------------------------------------------------------------------ #

    def _apply_overlap(
        self, text: str, chunks: list[tuple[int, int]]
    ) -> list[tuple[int, int]]:
        """Extend each chunk's start backwards by ~``overlap`` tokens.

        The overlap region is taken from the *end* of the previous chunk and
        trimmed forward to the next word boundary so chunks never start
        mid-word. Word boundaries are detected with :py:meth:`str.isspace`,
        which works for both Latin and Devanagari (the inter-word space is
        plain U+0020 in both scripts).
        """
        adjusted: list[tuple[int, int]] = [chunks[0]]
        for i in range(1, len(chunks)):
            cur_start, cur_end = chunks[i]
            prev_start, prev_end = chunks[i - 1]

            new_start = self._compute_overlap_start(text, prev_start, prev_end)
            # Never extend past the previous chunk's start (keep overlap a strict
            # subset of the previous chunk) and never past the current start
            # (no inversion).
            new_start = max(new_start, prev_start)
            new_start = min(new_start, cur_start)
            adjusted.append((new_start, cur_end))
        return adjusted

    def _compute_overlap_start(self, text: str, prev_start: int, prev_end: int) -> int:
        """Compute char offset such that the slice (offset, prev_end) is
        approximately ``self.overlap`` tokens, trimmed to a word boundary.
        """
        prev_text = text[prev_start:prev_end]
        if not prev_text:
            return prev_end

        # Use offset_mapping to find the char position of the Nth-from-last token.
        encoding = self.tokenizer(
            prev_text,
            add_special_tokens=False,
            return_offsets_mapping=True,
        )
        offsets = encoding["offset_mapping"]

        if len(offsets) <= self.overlap:
            # The whole previous chunk is overlap.
            return prev_start

        overlap_char_in_prev = offsets[-self.overlap][0]

        # Word-boundary trim: if we landed mid-word (previous char is non-space
        # AND non-empty), advance to the next whitespace, then skip past
        # whitespace to land on the start of the next word.
        if overlap_char_in_prev > 0 and not prev_text[overlap_char_in_prev - 1].isspace():
            n = len(prev_text)
            while overlap_char_in_prev < n and not prev_text[overlap_char_in_prev].isspace():
                overlap_char_in_prev += 1
            while overlap_char_in_prev < n and prev_text[overlap_char_in_prev].isspace():
                overlap_char_in_prev += 1

        return prev_start + overlap_char_in_prev


# ---------------------------------------------------------------------- #
# Module-level helpers
# ---------------------------------------------------------------------- #


def _split_keeping_separator(text: str, sep: str) -> list[str]:
    """Split ``text`` on ``sep``, attaching each separator to its preceding piece.

    Concatenating the result reproduces ``text`` exactly. Empty trailing pieces
    are dropped (so ``text`` ending in ``sep`` doesn't produce a trailing "").
    """
    if not sep:
        return [text]
    parts = text.split(sep)
    if len(parts) == 1:
        return parts
    out: list[str] = []
    for i, part in enumerate(parts):
        if i < len(parts) - 1:
            out.append(part + sep)
        elif part:
            out.append(part)
    # Drop empty leading entries (e.g., text starting with the separator).
    return [p for p in out if p]
