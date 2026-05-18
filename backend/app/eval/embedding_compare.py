"""Head-to-head comparison of multiple embedders on the same benchmark.

For each embedder the workflow is:

1. Build a fresh :class:`FaissStore` for that embedder's dimensionality.
2. Embed the corpus (passages) using ``encode_passages``.
3. Add them to the store with ``doc_id`` preserved as metadata.
4. Wrap in a :class:`DenseRetriever` (which uses ``encode_queries`` for queries).
5. Evaluate against the benchmark queries.

Output: one :class:`ComparisonReport` aggregating per-embedder
:class:`BenchmarkReport` s. The report writer (``app.eval.report``)
turns this into the final markdown table.

Kept separate from :mod:`app.eval.benchmark` so this module can be
imported without dragging in the embedder / FAISS stack (useful for
tests of the benchmark runner that don't compare embedders).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.embeddings.base import EmbeddingModel
from app.eval.benchmark import (
    BenchmarkQuery,
    BenchmarkReport,
    CorpusPassage,
    evaluate,
)
from app.retrieval.retriever import DenseRetriever
from app.retrieval.vector_store import FaissStore

logger = logging.getLogger(__name__)


@dataclass
class ComparisonReport:
    """Benchmark results keyed by embedder name."""

    dataset: str
    n_queries: int
    per_embedder: dict[str, BenchmarkReport] = field(default_factory=dict)

    def summary_table(self) -> list[dict[str, Any]]:
        """Rows for the comparison markdown table."""
        return [
            {
                "embedder": name,
                "recall@1": r.recall_at_1,
                "recall@5": r.recall_at_5,
                "recall@10": r.recall_at_10,
                "mrr@10": r.mrr_at_10,
                "ndcg@10": r.ndcg_at_10,
            }
            for name, r in self.per_embedder.items()
        ]


def build_retriever(
    embedder: EmbeddingModel,
    corpus: list[CorpusPassage],
    *,
    index_type: str = "flat",
    batch_size: int = 32,
    show_progress: bool = False,
) -> DenseRetriever:
    """Encode ``corpus`` with ``embedder`` and build a searchable retriever.

    Passages are embedded via ``encode_passages`` (E5-style prefixes apply)
    and stored with their full metadata, including the external ``doc_id``
    which the evaluator matches against.
    """
    texts = [p.text for p in corpus]
    logger.info("Encoding %d passages with %s", len(texts), embedder.name)
    vecs = embedder.encode_passages(
        texts, batch_size=batch_size, show_progress=show_progress
    )

    store = FaissStore(dim=embedder.dim, index_type=index_type)  # type: ignore[arg-type]
    store.add(vecs, metadatas=[p.to_metadata() for p in corpus])
    return DenseRetriever(embedder, store)


def compare_embedders(
    embedders: dict[str, EmbeddingModel],
    corpus: list[CorpusPassage],
    queries: list[BenchmarkQuery],
    *,
    dataset_name: str = "benchmark",
    index_type: str = "flat",
    batch_size: int = 32,
    show_progress: bool = False,
) -> ComparisonReport:
    """Run ``queries`` against every embedder in ``embedders`` on ``corpus``.

    Parameters
    ----------
    embedders:
        Mapping ``{name: embedder_instance}``. Names appear in the output.
    corpus:
        Loaded via :func:`app.eval.benchmark.load_corpus`.
    queries:
        Loaded via :func:`app.eval.benchmark.load_queries`.

    Returns
    -------
    ComparisonReport
        One :class:`BenchmarkReport` per embedder, plus the dataset name
        and query count for context.
    """
    report = ComparisonReport(dataset=dataset_name, n_queries=len(queries))
    for name, embedder in embedders.items():
        logger.info("=== evaluating embedder: %s ===", name)
        retriever = build_retriever(
            embedder,
            corpus,
            index_type=index_type,
            batch_size=batch_size,
            show_progress=show_progress,
        )
        report.per_embedder[name] = evaluate(
            retriever,
            queries,
            dataset_name=dataset_name,
            show_progress=show_progress,
        )
    return report
