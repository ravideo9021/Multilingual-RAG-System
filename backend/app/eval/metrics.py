"""Retrieval evaluation metrics.

Pure-Python implementations of the standard IR metrics. All functions
operate on lists of **document IDs** (any hashable type — strings, ints,
tuples). Binary relevance only: a doc is either relevant or not; graded
relevance is out of scope here.

Conventions:

* ``relevant_ids``: the set of docs that are "correct" for a query. Order
  does not matter.
* ``retrieved_ids``: the ranked list produced by the retriever, best first.
* ``k``: truncation cutoff. Metrics consider only the top-``k`` retrieved.

If ``relevant_ids`` is empty, metrics return ``None`` so downstream
aggregation can skip the query cleanly (rather than biasing the mean
toward 0).
"""

from __future__ import annotations

import math
from typing import Any, Hashable, Sequence

_ID = Hashable  # alias


def recall_at_k(
    relevant_ids: Sequence[_ID],
    retrieved_ids: Sequence[_ID],
    k: int,
) -> float | None:
    """Return 1.0 if *any* relevant id is in the top-``k``, else 0.0.

    This is the standard single-query binary Recall@k. Multi-graded Recall
    (fraction of relevant docs retrieved) is *not* used here — BEIR /
    MIRACL evaluate with binary hit/miss at each k.

    Returns ``None`` when there are no relevant docs (no way to evaluate).
    """
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    if not relevant_ids:
        return None
    relevant_set = set(relevant_ids)
    top = retrieved_ids[:k]
    return 1.0 if any(rid in relevant_set for rid in top) else 0.0


def mrr_at_k(
    relevant_ids: Sequence[_ID],
    retrieved_ids: Sequence[_ID],
    k: int,
) -> float | None:
    """Reciprocal rank of the first relevant doc in the top-``k``.

    ``1/rank`` where rank is 1-indexed. 0.0 if no relevant doc in top-``k``.
    ``None`` if there are no relevant docs at all.
    """
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    if not relevant_ids:
        return None
    relevant_set = set(relevant_ids)
    for rank, rid in enumerate(retrieved_ids[:k], start=1):
        if rid in relevant_set:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(
    relevant_ids: Sequence[_ID],
    retrieved_ids: Sequence[_ID],
    k: int,
) -> float | None:
    """Normalized Discounted Cumulative Gain at ``k`` (binary relevance).

    DCG = Σ (rel_i / log2(rank + 1)) for rank 1..k
    IDCG = DCG under a perfect ranking (all relevant docs first)
    nDCG = DCG / IDCG

    Returns a value in ``[0, 1]``. ``None`` if there are no relevant docs.
    """
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    if not relevant_ids:
        return None
    relevant_set = set(relevant_ids)

    dcg = 0.0
    for rank, rid in enumerate(retrieved_ids[:k], start=1):
        if rid in relevant_set:
            dcg += 1.0 / math.log2(rank + 1)

    n_rel_in_topk = min(len(relevant_set), k)
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, n_rel_in_topk + 1))
    if idcg == 0.0:
        return 0.0
    return dcg / idcg


def mean(values: Sequence[float | None]) -> float:
    """Arithmetic mean, skipping ``None``.

    Returns 0.0 on empty / all-None input — the caller should also track
    the count of contributing values so a degenerate "0.0 over 0 queries"
    result is distinguishable from a legitimate 0.0.
    """
    vals = [v for v in values if v is not None]
    if not vals:
        return 0.0
    return sum(vals) / len(vals)
