"""Reciprocal Rank Fusion (Cormack et al., 2009).

RRF merges multiple ranked lists into one. Given a document ``d`` appearing at
rank ``r`` (1-indexed) in list ``L``, its contribution from that list is
``1 / (k + r)``. The fused score is the sum over all lists in which ``d``
appears.

Key properties:

* **Rank-only.** Raw scores from the source lists are ignored — only their
  relative order matters. This is why RRF works well when fusing results
  from heterogeneous rankers (BM25 + dense, hi-query + en-query, etc.)
  whose score scales are incomparable.
* **k parameter** (typically 60) damps the influence of high-rank docs so
  a doc that's #1 in one list and missing from others can still be beaten
  by a doc that's consistently top-5 across several lists.

The fused list preserves the metadata from the **first** occurrence of each
document (across all input lists), and replaces its ``score`` with the fused
RRF score.

Each input item must have a stable ``id`` field for deduplication.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    ranked_lists: list[list[dict[str, Any]]],
    k: int = 60,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """Fuse ranked hit lists using Reciprocal Rank Fusion.

    Parameters
    ----------
    ranked_lists:
        One or more ranked result lists. Each list is ordered best-to-worst.
        Every item must be a dict with at least an ``id`` key. Empty lists
        (including the outer list) are tolerated.
    k:
        RRF damping constant. Must be ≥ 1. Common choice: 60.
    top_k:
        If given, truncate the fused output to this many items. ``None``
        returns every document that appeared in any input list.

    Returns
    -------
    list[dict]
        Fused, sorted best-to-worst. Each dict carries the merged metadata
        from the first list in which the doc appeared, with its ``score``
        replaced by the fused RRF score.
    """
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")

    if not ranked_lists:
        return []

    # id -> accumulated RRF score
    scores: dict[Any, float] = {}
    # id -> first-seen metadata dict (used as the "canonical" entry)
    first_seen: dict[Any, dict[str, Any]] = {}

    for rlist in ranked_lists:
        for rank, hit in enumerate(rlist, start=1):
            if "id" not in hit:
                raise KeyError(f"RRF input items must have an 'id' field; got keys {list(hit.keys())}")
            doc_id = hit["id"]
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
            if doc_id not in first_seen:
                first_seen[doc_id] = hit

    # Order by fused score desc, tiebreak by insertion order (dict preserves it,
    # which corresponds to first-seen order across the input lists).
    fused: list[dict[str, Any]] = []
    for doc_id, score in sorted(
        scores.items(),
        key=lambda kv: kv[1],
        reverse=True,
    ):
        entry = dict(first_seen[doc_id])  # shallow copy so we don't mutate input
        entry["score"] = score
        fused.append(entry)

    if top_k is not None:
        fused = fused[:top_k]
    return fused
