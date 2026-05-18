#!/usr/bin/env python
"""Embed a unified corpus JSONL and save a FAISS index to disk.

Two use cases:

1. Build the production index from the demo Wikipedia corpus:

   .. code-block:: console

       python scripts/build_index.py \\
           --corpus backend/data/sample_corpus/ingested.jsonl \\
           --out backend/data/index/bge-m3

2. Build an eval index from ``prepare_benchmark.py``'s corpus:

   .. code-block:: console

       python scripts/build_index.py \\
           --corpus backend/data/benchmark/corpus.jsonl \\
           --out backend/data/index/eval-bge-m3

Each output directory ends up with ``index.faiss``, ``metadata.sqlite``, and
``config.json`` — loadable via :meth:`FaissStore.load`.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--corpus", type=Path, required=True,
                        help="Path to corpus JSONL (doc_id + text per line)")
    parser.add_argument("--out", type=Path, required=True,
                        help="Output directory for the saved FaissStore")
    parser.add_argument("--embedder", default=None,
                        help="Embedder name (default: settings.embedding_model)")
    parser.add_argument("--device", default=None,
                        help="Device override (default: settings.device)")
    parser.add_argument("--index-type", default=None, choices=["flat", "ivfpq"],
                        help="FAISS index type (default: settings.faiss_index_type)")
    parser.add_argument("--batch-size", type=int, default=None,
                        help="Embedding batch size (default: settings.embedding_batch_size)")
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    from app.config import settings
    from app.embeddings import get_embedder
    from app.eval.benchmark import load_corpus
    from app.retrieval.vector_store import FaissStore

    embedder_name = args.embedder or settings.embedding_model
    device = args.device or settings.device
    index_type = args.index_type or settings.faiss_index_type
    batch_size = args.batch_size or settings.embedding_batch_size

    logger.info("Loading corpus from %s", args.corpus)
    corpus = load_corpus(args.corpus)
    logger.info("Corpus size: %d passages", len(corpus))
    if not corpus:
        logger.error("Empty corpus — nothing to index")
        return 1

    logger.info("Instantiating embedder=%s device=%s", embedder_name, device)
    embedder = get_embedder(embedder_name, device=device)

    logger.info("Encoding %d passages (batch=%d)…", len(corpus), batch_size)
    vecs = embedder.encode_passages(
        [p.text for p in corpus],
        batch_size=batch_size,
        show_progress=True,
    )

    logger.info("Building %s index (dim=%d)", index_type, embedder.dim)
    store = FaissStore(dim=embedder.dim, index_type=index_type)
    store.add(vecs, metadatas=[p.to_metadata() for p in corpus])

    out = Path(args.out)
    logger.info("Saving to %s", out)
    store.save(out)
    logger.info("Done. ntotal=%d", len(store))
    return 0


if __name__ == "__main__":
    sys.exit(main())
