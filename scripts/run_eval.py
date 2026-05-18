#!/usr/bin/env python
"""Run the benchmark eval and emit REPORT.md + eval_results/*.json.

Two modes, selected by flags:

* ``--single`` (default) evaluates one embedder against the benchmark.
* ``--compare`` runs every embedder in ``--embedders`` against the same
  benchmark and emits a comparison table.

The benchmark corpus must already exist (run ``prepare_benchmark.py``
first). Indexing is done in-memory for the duration of the run — it's
not persisted, because comparing embedders means building N indices at
different dimensionalities.

Usage
-----

.. code-block:: console

    # Single embedder, using the one in settings
    python scripts/run_eval.py --single

    # Compare bge-m3 vs e5
    python scripts/run_eval.py --compare --embedders bge-m3 e5
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--single", action="store_true",
                      help="Evaluate one embedder (default)")
    mode.add_argument("--compare", action="store_true",
                      help="Compare multiple embedders side-by-side")
    parser.add_argument("--embedders", nargs="+", default=None,
                        help="Embedders to run (compare mode). "
                             "Default: bge-m3 e5 (openai needs an API key).")
    parser.add_argument("--corpus", type=Path, default=None,
                        help="Corpus JSONL (default: backend/data/benchmark/corpus.jsonl)")
    parser.add_argument("--queries", type=Path, default=None,
                        help="Queries JSONL (default: backend/data/benchmark/queries.jsonl)")
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="Directory for JSON results (default: <repo>/eval_results/)")
    parser.add_argument("--report-path", type=Path, default=None,
                        help="Where to write REPORT.md (default: <repo>/REPORT.md)")
    parser.add_argument("--device", default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    from app.config import settings
    from app.embeddings import get_embedder
    from app.eval.benchmark import evaluate, load_corpus, load_queries
    from app.eval.embedding_compare import compare_embedders
    from app.eval.report import render_markdown, write_json, write_markdown
    from app.retrieval.vector_store import FaissStore
    from app.retrieval.retriever import DenseRetriever

    repo_root = Path(__file__).resolve().parent.parent
    corpus_path = args.corpus or repo_root / "backend" / "data" / "benchmark" / "corpus.jsonl"
    queries_path = args.queries or repo_root / "backend" / "data" / "benchmark" / "queries.jsonl"
    out_dir = args.out_dir or repo_root / "eval_results"
    report_path = args.report_path or repo_root / "REPORT.md"
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Loading benchmark: %s / %s", corpus_path, queries_path)
    corpus = load_corpus(corpus_path)
    queries = load_queries(queries_path)
    logger.info("Loaded %d passages, %d queries", len(corpus), len(queries))

    device = args.device or settings.device
    batch_size = args.batch_size or settings.embedding_batch_size

    if args.compare:
        names = args.embedders or ["bge-m3", "e5"]
        embedders = {name: get_embedder(name, device=device) for name in names}
        report = compare_embedders(
            embedders,
            corpus,
            queries,
            dataset_name="miracl-hi+xortydi (mini)",
            batch_size=batch_size,
            show_progress=True,
        )
        write_json(out_dir / "compare.json", report)
        md = render_markdown(
            title="Cross-lingual RAG — embedding comparison",
            comparison=report,
            notes=_notes_text(corpus_path, queries_path),
        )
        write_markdown(report_path, md)
        # Headline console line.
        for name, r in report.per_embedder.items():
            logger.info(
                "  %s: Recall@5=%.3f  MRR@10=%.3f  nDCG@10=%.3f",
                name, r.recall_at_5, r.mrr_at_10, r.ndcg_at_10,
            )
    else:
        # Single-embedder mode.
        name = (args.embedders or [settings.embedding_model])[0]
        embedder = get_embedder(name, device=device)
        logger.info("Encoding corpus with %s (dim=%d)", name, embedder.dim)
        vecs = embedder.encode_passages(
            [p.text for p in corpus], batch_size=batch_size, show_progress=True
        )
        store = FaissStore(dim=embedder.dim, index_type=settings.faiss_index_type)  # type: ignore[arg-type]
        store.add(vecs, metadatas=[p.to_metadata() for p in corpus])
        retriever = DenseRetriever(embedder, store)
        report = evaluate(
            retriever,
            queries,
            dataset_name="miracl-hi+xortydi (mini)",
            show_progress=True,
        )
        write_json(out_dir / f"single-{name}.json", report)
        md = render_markdown(
            title=f"Cross-lingual RAG — retrieval eval ({name})",
            single_report=report,
            notes=_notes_text(corpus_path, queries_path),
        )
        write_markdown(report_path, md)
        logger.info(
            "  %s: Recall@5=%.3f  MRR@10=%.3f  nDCG@10=%.3f",
            name, report.recall_at_5, report.mrr_at_10, report.ndcg_at_10,
        )

    logger.info("Wrote %s", report_path)
    return 0


def _notes_text(corpus_path: Path, queries_path: Path) -> str:
    return (
        "This evaluation uses a **scaled-down** subset of MIRACL-hi and XOR-TyDi, "
        "prepared via `scripts/prepare_benchmark.py`. The corpus contains all "
        "gold passages plus a fixed pool of distractors (see `--distractors` "
        "flag used when preparing the benchmark). The resulting numbers are "
        "not directly comparable to published MIRACL / XOR-TyDi scores, but "
        "they are reproducible and internally consistent for comparing "
        f"embedders.\n\n"
        f"- Corpus: `{corpus_path}`\n"
        f"- Queries: `{queries_path}`\n"
    )


if __name__ == "__main__":
    sys.exit(main())
