#!/usr/bin/env python
"""Adapt MIRACL-hi and XOR-TyDi into this project's unified benchmark format.

Output files
------------
``backend/data/benchmark/queries.jsonl``
    One :class:`BenchmarkQuery` per line.
``backend/data/benchmark/corpus.jsonl``
    One :class:`CorpusPassage` per line — the union of gold passages across
    all selected queries, plus a pool of random distractor passages.

Scaled-down by design
---------------------
MIRACL-hi's full Wikipedia corpus has ~500K passages. Indexing that with
BGE-M3 on CPU takes hours and is prohibitive for a portfolio demo. Instead,
this script builds a *mini benchmark*:

* Sample ``--max-queries`` queries (default 100) from each source dataset.
* Collect the union of their relevant passages.
* Add ``--distractors`` randomly-sampled passages (default 2000) that are
  NOT relevant to any sampled query.
* Write corpus + queries in unified JSONL.

The resulting eval is **not** the canonical MIRACL/XOR-TyDi score — it's a
scaled-down, reproducible approximation. REPORT.md calls this out
explicitly so the number is not misrepresented.

Usage
-----

.. code-block:: console

    python scripts/prepare_benchmark.py                       # full run
    python scripts/prepare_benchmark.py --max-queries 20      # tiny dev
    python scripts/prepare_benchmark.py --miracl-only         # skip XOR-TyDi

Both datasets require HuggingFace `datasets` to be installed (already in
``pyproject.toml``). MIRACL requires acceptance of its license on HF — run
``huggingface-cli login`` once if you haven't.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------- #
# MIRACL-hi adapter
# ---------------------------------------------------------------------- #


def load_miracl_hi(
    max_queries: int | None,
    seed: int,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Load MIRACL-hi dev split + its Hindi corpus.

    Returns ``(queries, passages_by_id)`` where:

    * ``queries``: list of unified-format query dicts (not yet written)
    * ``passages_by_id``: mapping ``{doc_id: {"text", "title", ...}}``
      for every passage referenced by any returned query plus (lazily
      by the caller) additional random distractors.
    """
    from datasets import load_dataset

    logger.info("Loading miracl/miracl hi (dev) …")
    ds_queries = load_dataset("miracl/miracl", "hi", split="dev")

    # The corpus is a separate dataset. We only need the passages referenced
    # by the queries we sample (plus distractors added by the caller).
    logger.info("Loading miracl/miracl-corpus hi …")
    ds_corpus = load_dataset("miracl/miracl-corpus", "hi", split="train")

    # Index the corpus by docid for fast lookup. Each row: {"docid", "title", "text"}.
    logger.info("Indexing %d MIRACL-hi corpus passages by docid", len(ds_corpus))
    passages_by_id: dict[str, dict[str, Any]] = {}
    for row in ds_corpus:
        passages_by_id[str(row["docid"])] = {
            "doc_id": f"miracl-hi:{row['docid']}",
            "text": row["text"],
            "title": row.get("title", ""),
            "language": "hi",
            "source": "miracl-hi",
        }

    # Sample queries.
    rng = random.Random(seed)
    query_indices = list(range(len(ds_queries)))
    if max_queries is not None and max_queries < len(query_indices):
        query_indices = rng.sample(query_indices, max_queries)

    queries: list[dict[str, Any]] = []
    seen_doc_ids: set[str] = set()
    for idx in query_indices:
        q_row = ds_queries[idx]
        # Positive passages have relevance=1; negatives have relevance=0.
        positive_ids = [
            str(p["docid"])
            for p in q_row.get("positive_passages", [])
        ]
        # Skip queries with no positives — not scorable.
        if not positive_ids:
            continue
        relevant = [f"miracl-hi:{pid}" for pid in positive_ids]
        seen_doc_ids.update(relevant)
        queries.append(
            {
                "qid": f"miracl-hi:{q_row['query_id']}",
                "query": q_row["query"],
                "query_lang": "hi",
                "target_lang": "hi",
                "relevant_doc_ids": relevant,
                "source_dataset": "miracl-hi",
            }
        )

    # Trim passages_by_id to just the ones we need (saves memory before
    # the caller mixes in distractors).
    needed_ids = {pid for q in queries for pid in q["relevant_doc_ids"]}
    kept = {k: v for k, v in passages_by_id.items() if f"miracl-hi:{k}" in needed_ids}
    # Note: we keep the *full* dict under the caller's control for distractor sampling.
    # Here we return the full dict indexed by the raw docid (no prefix).
    return queries, passages_by_id


# ---------------------------------------------------------------------- #
# XOR-TyDi adapter
# ---------------------------------------------------------------------- #


def load_xortydi(
    max_queries: int | None,
    seed: int,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Load XOR-TyDi Hindi queries (English questions, Hindi answer corpus).

    XOR-TyDi's structure is looser than MIRACL — it provides questions and
    gold Wikipedia URLs / passage snippets rather than a clean doc-id list.
    For the mini-benchmark we treat each gold passage text as its own doc
    with a synthetic id.

    The HF dataset id is ``akariasai/xor_tydi_qa``; the ``xor_retrieve``
    split is what we want (question + gold passages).
    """
    from datasets import load_dataset

    logger.info("Loading akariasai/xor_tydi_qa (dev) …")
    ds = load_dataset("akariasai/xor_tydi_qa", split="validation")

    # Filter to Hindi-target rows.
    hi_rows = [row for row in ds if row.get("lang") == "hi"]
    logger.info("XOR-TyDi Hindi dev rows: %d", len(hi_rows))

    rng = random.Random(seed + 1)  # different seed stream from MIRACL
    if max_queries is not None and max_queries < len(hi_rows):
        hi_rows = rng.sample(hi_rows, max_queries)

    queries: list[dict[str, Any]] = []
    passages_by_id: dict[str, dict[str, Any]] = {}

    for i, row in enumerate(hi_rows):
        question = row["question"]
        # Gold answers are strings — we wrap them into pseudo-passages.
        # XOR-TyDi's retrieval split varies in field names by HF release.
        # We look for "answers" and "gold_passages" fields defensively.
        gold_passages = row.get("gold_passages") or row.get("answers") or []
        if not gold_passages:
            continue

        relevant_doc_ids: list[str] = []
        for j, passage in enumerate(gold_passages):
            # Some splits give {"title", "text"}; others give plain strings.
            if isinstance(passage, dict):
                text = passage.get("text") or passage.get("answer") or ""
                title = passage.get("title", "")
            else:
                text = str(passage)
                title = ""
            if not text:
                continue
            doc_id = f"xortydi:q{i}-p{j}"
            passages_by_id[doc_id.split(":", 1)[1]] = {
                "doc_id": doc_id,
                "text": text,
                "title": title,
                "language": "hi",
                "source": "xor-tydi",
            }
            relevant_doc_ids.append(doc_id)

        if not relevant_doc_ids:
            continue

        queries.append(
            {
                "qid": f"xortydi:q{i}",
                "query": question,
                "query_lang": "en",  # XOR-TyDi questions are English
                "target_lang": "hi",
                "relevant_doc_ids": relevant_doc_ids,
                "source_dataset": "xor-tydi",
            }
        )

    return queries, passages_by_id


# ---------------------------------------------------------------------- #
# Distractor sampling
# ---------------------------------------------------------------------- #


def sample_distractors(
    passages_by_id: dict[str, dict[str, Any]],
    already_used_doc_ids: set[str],
    n: int,
    seed: int,
) -> list[dict[str, Any]]:
    """Randomly sample ``n`` passages that are NOT already in the relevant set."""
    rng = random.Random(seed + 7)
    candidates = [
        (raw_id, passage)
        for raw_id, passage in passages_by_id.items()
        if passage["doc_id"] not in already_used_doc_ids
    ]
    if n > len(candidates):
        logger.warning(
            "Requested %d distractors but only %d available; using all", n, len(candidates)
        )
        return [p for _, p in candidates]
    sampled = rng.sample(candidates, n)
    return [p for _, p in sampled]


# ---------------------------------------------------------------------- #
# Writer
# ---------------------------------------------------------------------- #


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return n


# ---------------------------------------------------------------------- #
# Main
# ---------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--max-queries", type=int, default=100,
                        help="Sample this many queries per source (default: 100)")
    parser.add_argument("--distractors", type=int, default=2000,
                        help="Extra random non-relevant passages to index (default: 2000)")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--miracl-only", action="store_true")
    parser.add_argument("--xortydi-only", action="store_true")
    parser.add_argument("--out", type=Path, default=None,
                        help="Output directory (default: backend/data/benchmark/)")
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    if args.miracl_only and args.xortydi_only:
        parser.error("--miracl-only and --xortydi-only are mutually exclusive")

    out_dir = args.out
    if out_dir is None:
        repo_root = Path(__file__).resolve().parent.parent
        out_dir = repo_root / "backend" / "data" / "benchmark"
    out_dir = Path(out_dir)

    all_queries: list[dict[str, Any]] = []
    # Combined id → passage pool (MIRACL corpus + XOR-TyDi pseudo-passages).
    # Note: MIRACL keys are raw docids; XOR-TyDi keys are "qN-pM".
    # Collision is impossible because the prefix forms differ.
    combined_pool: dict[str, dict[str, Any]] = {}

    if not args.xortydi_only:
        try:
            m_queries, m_pool = load_miracl_hi(args.max_queries, args.seed)
            all_queries.extend(m_queries)
            combined_pool.update(m_pool)
            logger.info("MIRACL-hi: %d queries, %d corpus passages", len(m_queries), len(m_pool))
        except Exception as exc:  # noqa: BLE001 — surface any adapter error
            logger.error("MIRACL-hi load failed: %s", exc)
            if not args.miracl_only:
                logger.warning("Continuing with XOR-TyDi only")

    if not args.miracl_only:
        try:
            x_queries, x_pool = load_xortydi(args.max_queries, args.seed)
            all_queries.extend(x_queries)
            # XOR-TyDi passages use synthetic ids; merging is safe.
            for raw_id, passage in x_pool.items():
                combined_pool[f"xortydi-{raw_id}"] = passage
            logger.info("XOR-TyDi: %d queries, %d pseudo-passages", len(x_queries), len(x_pool))
        except Exception as exc:  # noqa: BLE001
            logger.error("XOR-TyDi load failed: %s", exc)

    if not all_queries:
        logger.error("No queries loaded from any source — aborting")
        return 1

    # Build the corpus: relevant passages for every selected query + distractors.
    used_doc_ids: set[str] = {
        did for q in all_queries for did in q["relevant_doc_ids"]
    }
    logger.info("Gold passages referenced: %d", len(used_doc_ids))

    # The relevant passages are a subset of combined_pool (keyed differently).
    relevant_corpus = [
        p for p in combined_pool.values() if p["doc_id"] in used_doc_ids
    ]

    if args.distractors > 0:
        distractors = sample_distractors(
            combined_pool, used_doc_ids, args.distractors, args.seed
        )
        logger.info("Adding %d distractor passages", len(distractors))
    else:
        distractors = []

    corpus = relevant_corpus + distractors
    # Shuffle so distractors don't all cluster at the end — makes the order
    # in the jsonl slightly less revealing.
    random.Random(args.seed + 13).shuffle(corpus)

    queries_out = out_dir / "queries.jsonl"
    corpus_out = out_dir / "corpus.jsonl"

    n_q = write_jsonl(queries_out, all_queries)
    n_c = write_jsonl(corpus_out, corpus)

    logger.info("Wrote %d queries → %s", n_q, queries_out)
    logger.info("Wrote %d passages (%d relevant + %d distractors) → %s",
                n_c, len(relevant_corpus), len(distractors), corpus_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
