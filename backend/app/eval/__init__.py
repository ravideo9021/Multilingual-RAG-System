"""Evaluation: retrieval metrics, benchmark loader/runner, embedding comparison.

RAGAS (generation-side) evaluation lives under :mod:`app.generation` — it
can't be built until the LLM-backed generator exists (Chunk E).
"""

from app.eval.benchmark import (
    BenchmarkQuery,
    BenchmarkReport,
    CorpusPassage,
    PerQueryResult,
    evaluate,
    load_corpus,
    load_queries,
)
from app.eval.embedding_compare import (
    ComparisonReport,
    build_retriever,
    compare_embedders,
)
from app.eval.metrics import mean, mrr_at_k, ndcg_at_k, recall_at_k
from app.eval.report import (
    PLACEHOLDER,
    render_markdown,
    write_json,
    write_markdown,
)

__all__ = [
    "BenchmarkQuery",
    "BenchmarkReport",
    "ComparisonReport",
    "CorpusPassage",
    "PLACEHOLDER",
    "PerQueryResult",
    "build_retriever",
    "compare_embedders",
    "evaluate",
    "load_corpus",
    "load_queries",
    "mean",
    "mrr_at_k",
    "ndcg_at_k",
    "recall_at_k",
    "render_markdown",
    "write_json",
    "write_markdown",
]
