"""File-type-aware text extraction for ingestion.

The /ingest endpoint accepts PDFs, HTML, plain text, and Markdown. Each
needs a different extraction strategy — naively UTF-8 decoding a PDF
yields garbled binary which then poisons the index. ``extract_text``
dispatches on file extension (with a content-sniff fallback for ``.bin``
or extension-less uploads) and returns plain text.

Extractors used:
    * PDF  — :mod:`pypdf` (already a project dependency).
    * HTML — :mod:`bs4` (BeautifulSoup), ``lxml`` parser if available else ``html.parser``.
    * TXT/MD — UTF-8 decode with ``errors="replace"``.
"""

from __future__ import annotations

import logging
from pathlib import PurePosixPath

logger = logging.getLogger(__name__)


class ExtractionError(ValueError):
    """Raised when a file's text could not be extracted (corrupt / image-only PDF / etc.)."""


def _looks_like_pdf(content: bytes) -> bool:
    return content[:5] == b"%PDF-"


def _looks_like_html(content: bytes) -> bool:
    head = content[:512].lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html") or b"<body" in head


def _extract_pdf(content: bytes) -> str:
    """Extract text from a PDF byte string using pypdf.

    Returns the concatenated text of all pages (separated by blank lines).
    Pages with no extractable text (e.g. scanned images) are silently
    skipped — a fully image-only PDF will return ``""`` and the caller
    should surface that to the user.
    """
    import io

    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(content))
    except Exception as exc:
        raise ExtractionError(f"Could not parse PDF: {exc}") from exc

    pages: list[str] = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            logger.warning("PDF page %d extraction failed: %s", i + 1, exc)
            continue
        text = text.strip()
        if text:
            pages.append(text)

    return "\n\n".join(pages)


def _extract_html(content: bytes) -> str:
    """Strip tags from HTML and return visible text."""
    from bs4 import BeautifulSoup

    try:
        soup = BeautifulSoup(content, "html.parser")
    except Exception as exc:
        raise ExtractionError(f"Could not parse HTML: {exc}") from exc

    # Drop script/style noise before grabbing text.
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    # Collapse runs of blank lines.
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def _extract_text(content: bytes) -> str:
    """Decode plain text / Markdown as UTF-8 (replacement on errors)."""
    return content.decode("utf-8", errors="replace")


def extract_text(filename: str, content: bytes) -> str:
    """Extract plain text from an uploaded file.

    Dispatch order:
        1. File extension (``.pdf``, ``.html``/``.htm``, ``.txt``/``.md``).
        2. Magic-byte sniff for PDFs / HTML when the extension is missing.
        3. Fall back to UTF-8 decode.

    Raises
    ------
    ExtractionError
        When the file looks like a supported format but parsing failed,
        or when the result is empty.
    """
    ext = PurePosixPath(filename or "").suffix.lower()

    if ext == ".pdf" or (not ext and _looks_like_pdf(content)):
        text = _extract_pdf(content)
    elif ext in {".html", ".htm"} or (not ext and _looks_like_html(content)):
        text = _extract_html(content)
    elif ext in {".txt", ".md", ".markdown", ".rst", ""}:
        text = _extract_text(content)
    else:
        # Unknown extension — try plain text and let downstream chunking
        # fail loudly if it's actually binary.
        logger.info("Unknown extension %r — falling back to UTF-8 decode", ext)
        text = _extract_text(content)

    text = text.strip()
    if not text:
        raise ExtractionError(
            "No text could be extracted from this file. "
            "If it's a scanned PDF, run OCR first; if it's binary, "
            "convert it to PDF or plain text."
        )
    return text
