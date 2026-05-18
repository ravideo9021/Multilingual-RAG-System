"""Unified benchmark format + retriever evaluator.

All cross-lingual benchmarks in this project (MIRACL-hi, XOR-TyDi, etc.)
are normalized to the same JSONL schema so one evaluator works for all.

Unified query schema (one JSON object per line):

.. code-block:: json

    {
      "qid": "miracl-hi-0042",
      "query": "भारत की राजधानी क्या है?",
      "query_lang": "hi",
      "target_lang": "hi",
      "relevant_doc_ids": ["miracl-hi-passage-123", "miracl-hi-passage-456"],
      "source_dataset": "miracl-hi",
      "metadata": {}
    }

Unified corpus schema (``corpus.jsonl`` — ingested into FAISS with the
``doc_id`` stored as chunk metadata, which is what the evaluator matches
against):

.. code-block:: json

    {
      "doc_id": "miracl-hi-passage-123",
      "text": "...",
      "language": "hi",
      "source": "miracl-hi",
      "title": "..."
    }

The evaluator pulls ``hit["doc_id"]`` from each retrieval result (i.e.,
the doc_id you stored as metadata when indexing). If you use the raw
FAISS integer id (``hit["id"]``) those will NEVER match the string
benchmark ids — always pass the external doc_id through metadata.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from app.eval.metrics import mean, mrr_at_k, ndcg_at_k, recall_at_k

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------- #
# Data models
# ---------------------------------------------------------------------- #


@dataclass
class BenchmarkQuery:
    """One evaluation query + its gold doc IDs."""

    qid: str
    query: str
    query_lang: str
    relevant_doc_ids: list[str]
    source_dataset: str
    target_lang: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "BenchmarkQuery":
        return cls(
            qid=str(d["qid"]),
            query=d["query"],
            query_lang=d["query_lang"],
            relevant_doc_ids=[str(x) for x in d.get("relevant_doc_ids", [])],
            source_dataset=d.get("source_dataset", "unknown"),
            target_lang=d.get("target_lang"),
            metadata=d.get("metadata", {}),
        )


@dataclass
class CorpusPassage:
    """One indexable passage with a stable external ``doc_id``."""

    doc_id: str
    text: str
    language: str = "unknown"
    source: str = ""
    title: str = ""

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CorpusPassage":
        return cls(
            doc_id=str(d["doc_id"]),
            text=d["text"],
            language=d.get("language", "unknown"),
            source=d.get("source", ""),
            title=d.get("title", ""),
        )

    def to_metadata(self) -> dict[str, Any]:
        """Metadata dict passed to :pymeth:`FaissStore.add`.

        Crucially includes ``doc_id`` so the evaluator can match it against
        ``BenchmarkQuery.relevant_doc_ids``.
        """
        return {
            "doc_id": self.doc_id,
            "text": self.text,
            "language": self.language,
            "source": self.source,
            "title": self.title,
        }


@dataclass
class PerQueryResult:
    qid: str
    query_lang: str
    source_dataset: str
    n_relevant: int
    retrieved_doc_ids: list[str]
    recall_at_1: float | None
    recall_at_5: float | None
    recall_at_10: float | None
    mrr_at_10: float | None
    ndcg_at_10: float | None


@dataclass
class BenchmarkReport:
    """Aggregate + per-query metrics for one retriever on one benchmark."""

    dataset: str
    n_queries: int
    n_scored: int  # queries with at least one relevant doc
    recall_at_1: float
    recall_at_5: float
    recall_at_10: float
    mrr_at_10: float
    ndcg_at_10: float
    per_query: list[PerQueryResult] = field(default_factory=list)
    # Optional breakdown by sub-dataset (e.g., within a merged MIRACL + XOR-TyDi run).
    by_source: dict[str, dict[str, float]] = field(default_factory=dict)

    def to_summary_dict(self) -> dict[str, Any]:
        """Compact dict for JSON reports (excludes per-query detail)."""
        return {
            "dataset": self.dataset,
            "n_queries": self.n_queries,
            "n_scored": self.n_scored,
            "recall_at_1": self.recall_at_1,
            "recall_at_5": self.recall_at_5,
            "recall_at_10": self.recall_at_10,
            "mrr_at_10": self.mrr_at_10,
            "ndcg_at_10": self.ndcg_at_10,
            "by_source": self.by_source,
        }


# ---------------------------------------------------------------------- #
# I/O
# ---------------------------------------------------------------------- #


def load_queries(path: str | Path) -> list[BenchmarkQuery]:
    """Load a JSONL benchmark query file."""
    path = Path(path)
    out: list[BenchmarkQuery] = []
    with path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(BenchmarkQuery.from_dict(json.loads(line)))
            except (KeyError, json.JSONDecodeError) as exc:
                raise ValueError(f"{path}:{lineno}: malformed query: {exc}") from exc
    logger.info("Loaded %d benchmark queries from %s", len(out), path)
    return out


def load_corpus(path: str | Path) -> list[CorpusPassage]:
    """Load a JSONL corpus file."""
    path = Path(path)
    out: list[CorpusPassage] = []
    with path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(CorpusPassage.from_dict(json.loads(line)))
            except (KeyError, json.JSONDecodeError) as exc:
                raise ValueError(f"{path}:{lineno}: malformed passage: {exc}") from exc
    logger.info("Loaded %d corpus passages from %s", len(out), path)
    return out


# ---------------------------------------------------------------------- #
# Retriever protocol — lets us test without a real DenseRetriever
# ---------------------------------------------------------------------- #


class RetrieverLike(Protocol):
    def retrieve(self, query: str, k: int = 5) -> list[dict[str, Any]]: ...


# ---------------------------------------------------------------------- #
# Evaluation
# ---------------------------------------------------------------------- #


def evaluate(
    retriever: RetrieverLike,
    queries: list[BenchmarkQuery],
    *,
    dataset_name: str = "benchmark",
    max_k: int = 10,
    show_progress: bool = False,
) -> BenchmarkReport:
    """Run ``queries`` through ``retriever`` and compute metrics.

    Parameters
    ----------
    retriever:
        Anything with a ``retrieve(query: str, k: int) -> list[dict]`` method.
        Each returned hit must include a ``doc_id`` key (string, external
        stable ID — NOT the FAISS integer id). If ``doc_id`` is missing
        we fall back to the ``id`` field so tests can work with a pure-FAISS
        setup, but that will silently return 0 recall against a real
        benchmark where relevant ids are strings.
    queries:
        Loaded via :func:`load_queries`.
    max_k:
        Top-``k`` ceiling for all retrieval calls. Metrics at k=1, 5, 10
        are computed; ``max_k`` must be ≥ 10.
    """
    if max_k < 10:
        raise ValueError(f"max_k must be >= 10 to compute @10 metrics; got {max_k}")

    iterator = queries
    if show_progress:
        try:
            from tqdm import tqdm

            iterator = tqdm(queries, desc=f"eval[{dataset_name}]")
        except ImportError:
            pass

    per_query: list[PerQueryResult] = []
    for q in iterator:
        hits = retriever.retrieve(q.query, k=max_k)
        retrieved_ids = [_hit_doc_id(h) for h in hits]
        per_query.append(
            PerQueryResult(
                qid=q.qid,
                query_lang=q.query_lang,
                source_dataset=q.source_dataset,
                n_relevant=len(q.relevant_doc_ids),
                retrieved_doc_ids=retrieved_ids,
                recall_at_1=recall_at_k(q.relevant_doc_ids, retrieved_ids, 1),
                recall_at_5=recall_at_k(q.relevant_doc_ids, retrieved_ids, 5),
                recall_at_10=recall_at_k(q.relevant_doc_ids, retrieved_ids, 10),
                mrr_at_10=mrr_at_k(q.relevant_doc_ids, retrieved_ids, 10),
                ndcg_at_10=ndcg_at_k(q.relevant_doc_ids, retrieved_ids, 10),
            )
        )

    n_scored = sum(1 for r in per_query if r.n_relevant > 0)

    report = BenchmarkReport(
        dataset=dataset_name,
        n_queries=len(queries),
        n_scored=n_scored,
        recall_at_1=mean([r.recall_at_1 for r in per_query]),
        recall_at_5=mean([r.recall_at_5 for r in per_query]),
        recall_at_10=mean([r.recall_at_10 for r in per_query]),
        mrr_at_10=mean([r.mrr_at_10 for r in per_query]),
        ndcg_at_10=mean([r.ndcg_at_10 for r in per_query]),
        per_query=per_query,
    )
    report.by_source = _breakdown_by_source(per_query)
    return report


def _hit_doc_id(hit: dict[str, Any]) -> str:
    """Extract the external doc_id from a retrieval hit.

    Falls back to ``id`` (FAISS integer) if ``doc_id`` is missing, so unit
    tests that don't round-trip metadata still work.
    """
    if "doc_id" in hit:
        return str(hit["doc_id"])
    return str(hit.get("id", ""))


def _breakdown_by_source(results: list[PerQueryResult]) -> dict[str, dict[str, float]]:
    """Group per-query results by source_dataset and aggregate each slice."""
    by_src: dict[str, list[PerQueryResult]] = {}
    for r in results:
        by_src.setdefault(r.source_dataset, []).append(r)
    out: dict[str, dict[str, float]] = {}
    for src, results_for_src in by_src.items():
        out[src] = {
            "n_queries": len(results_for_src),
            "recall_at_5": mean([r.recall_at_5 for r in results_for_src]),
            "recall_at_10": mean([r.recall_at_10 for r in results_for_src]),
            "mrr_at_10": mean([r.mrr_at_10 for r in results_for_src]),
            "ndcg_at_10": mean([r.ndcg_at_10 for r in results_for_src]),
        }
    return out
