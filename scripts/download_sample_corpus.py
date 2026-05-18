#!/usr/bin/env python
"""Download a small, matched Hindi/English Wikipedia corpus for the RAG demo.

Why matched pairs? Cross-lingual retrieval can only work if the corpus
contains meaningful content in both languages on overlapping topics. Random
Hindi + random English wouldn't exercise the cross-lingual path at all.

The topics are hand-curated (below) to give reasonable coverage of:
* Geography (major Indian states / cities)
* Historical figures
* Cultural topics (festivals, cuisine, cinema)
* Science / technology

Output
------
``backend/data/sample_corpus/`` contains one ``.txt`` file per article
and a ``manifest.jsonl`` that lists every article with its title,
language, and topic pair key. The ingestion pipeline (Chunk E) consumes
the manifest.

Usage
-----

.. code-block:: console

    python scripts/download_sample_corpus.py              # default ~25 pairs
    python scripts/download_sample_corpus.py --topics 5   # small dev run
    python scripts/download_sample_corpus.py --out /tmp/corpus
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


# Matched (English title, Hindi title) pairs. Hindi titles are the real
# names of the corresponding articles on hi.wikipedia.org — not machine
# translations. Verified by hand (some titles use slightly different
# conventions, e.g., "मुंबई" vs. "Bombay" ambiguity).
TOPIC_PAIRS: list[tuple[str, str]] = [
    # --- Geography (states / cities) ---
    ("India", "भारत"),
    ("Delhi", "दिल्ली"),
    ("Mumbai", "मुंबई"),
    ("Kolkata", "कोलकाता"),
    ("Bengaluru", "बंगलौर"),
    ("Chennai", "चेन्नई"),
    ("Hyderabad", "हैदराबाद"),
    ("Rajasthan", "राजस्थान"),
    ("Kerala", "केरल"),
    ("Uttar Pradesh", "उत्तर प्रदेश"),
    # --- History / politicians ---
    ("Mahatma Gandhi", "महात्मा गांधी"),
    ("Jawaharlal Nehru", "जवाहरलाल नेहरू"),
    ("B. R. Ambedkar", "भीमराव आम्बेडकर"),
    ("Subhas Chandra Bose", "सुभाष चंद्र बोस"),
    ("Indira Gandhi", "इंदिरा गांधी"),
    # --- Culture ---
    ("Bollywood", "बॉलीवुड"),
    ("Indian cuisine", "भारतीय खाना"),
    ("Diwali", "दीवाली"),
    ("Holi", "होली"),
    ("Taj Mahal", "ताजमहल"),
    # --- Sports ---
    ("Cricket in India", "भारत में क्रिकेट"),
    ("Sachin Tendulkar", "सचिन तेंदुलकर"),
    # --- Science / tech ---
    ("Indian Space Research Organisation", "भारतीय अंतरिक्ष अनुसंधान संगठन"),
    ("Aryabhata", "आर्यभट"),
    ("Indian Institute of Technology", "भारतीय प्रौद्योगिकी संस्थान"),
]


@dataclass
class Article:
    topic_key: str  # stable key matching the hi/en pair (uses English title)
    title: str
    language: str  # "hi" | "en"
    text: str


def fetch_article(wiki, title: str, language: str, topic_key: str) -> Article | None:
    """Fetch one article; return None if missing."""
    page = wiki.page(title)
    if not page.exists():
        logger.warning("[%s] page not found: %s", language, title)
        return None
    # .text returns plain prose without markup — good enough for our chunker.
    return Article(
        topic_key=topic_key,
        title=title,
        language=language,
        text=page.text,
    )


def fetch_pair(
    en_wiki, hi_wiki, en_title: str, hi_title: str
) -> list[Article]:
    topic_key = en_title  # stable across both languages
    articles: list[Article] = []
    en = fetch_article(en_wiki, en_title, "en", topic_key)
    if en is not None:
        articles.append(en)
    hi = fetch_article(hi_wiki, hi_title, "hi", topic_key)
    if hi is not None:
        articles.append(hi)
    return articles


def write_article(article: Article, out_dir: Path) -> Path:
    """Write one article as a .txt file; return its path."""
    # Filename: <topic_key slug>.<language>.txt
    slug = article.topic_key.lower().replace(" ", "_").replace(".", "").replace("/", "-")
    fname = f"{slug}.{article.language}.txt"
    path = out_dir / fname
    path.write_text(article.text, encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--topics",
        type=int,
        default=len(TOPIC_PAIRS),
        help="Number of topic pairs to download (default: all).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory (default: backend/data/sample_corpus/)",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.2,
        help="Seconds to sleep between requests to be polite (default: 0.2)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    try:
        import wikipediaapi
    except ImportError:
        logger.error(
            "wikipedia-api not installed. Run `cd backend && uv sync` first."
        )
        return 2

    out_dir = args.out
    if out_dir is None:
        # backend/data/sample_corpus relative to this script.
        repo_root = Path(__file__).resolve().parent.parent
        out_dir = repo_root / "backend" / "data" / "sample_corpus"
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # User-Agent is required by Wikipedia's API policy.
    user_agent = "multilingual-rag-demo/0.1 (educational; https://github.com/)"
    en_wiki = wikipediaapi.Wikipedia(user_agent=user_agent, language="en")
    hi_wiki = wikipediaapi.Wikipedia(user_agent=user_agent, language="hi")

    pairs = TOPIC_PAIRS[: args.topics]
    logger.info("Fetching %d topic pairs into %s", len(pairs), out_dir)

    manifest: list[dict] = []
    for i, (en_title, hi_title) in enumerate(pairs, start=1):
        logger.info("[%d/%d] %s / %s", i, len(pairs), en_title, hi_title)
        articles = fetch_pair(en_wiki, hi_wiki, en_title, hi_title)
        for art in articles:
            path = write_article(art, out_dir)
            manifest.append(
                {
                    "topic_key": art.topic_key,
                    "title": art.title,
                    "language": art.language,
                    "path": str(path.relative_to(out_dir)),
                    "char_count": len(art.text),
                }
            )
        if args.sleep > 0 and i < len(pairs):
            time.sleep(args.sleep)

    manifest_path = out_dir / "manifest.jsonl"
    with manifest_path.open("w", encoding="utf-8") as f:
        for entry in manifest:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    logger.info(
        "Done. %d articles (%d pairs requested) → %s",
        len(manifest), len(pairs), out_dir,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
