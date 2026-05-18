"""Relevance-threshold gating.

Filters retrieval results by a minimum score. Used to prevent the generator
from answering when no retrieved chunk clears a relevance bar — a critical
piece of the "I don't know" response path, since it lets us distinguish
"nothing relevant was found" from "the model hallucinated a refusal."

Note: when fusing ranked lists via RRF, the fused score is **not** a
cosine similarity — it's a rank-based sum. Apply thresholds to the
pre-fusion cosine scores, then fuse. See the query router for the
standard order.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def apply_threshold(
    results: list[dict[str, Any]],
    threshold: float,
) -> list[dict[str, Any]]:
    """Return only hits whose ``score`` field is ``>= threshold``.

    Preserves input order (assumed best-to-worst). Hits missing a ``score``
    key are dropped with a warning — callers should always populate it.

    Parameters
    ----------
    results:
        Retrieval results. Each item must have a numeric ``score`` field.
    threshold:
        Minimum score to keep. Cosine similarity is in ``[-1, 1]``; typical
        relevance thresholds for L2-normalized embeddings sit in ``[0.3, 0.5]``.

    Returns
    -------
    list[dict]
        Filtered results. Empty if nothing clears the bar.
    """
    out: list[dict[str, Any]] = []
    for hit in results:
        if "score" not in hit:
            logger.warning("Dropping hit with no 'score' field: id=%s", hit.get("id"))
            continue
        if hit["score"] >= threshold:
            out.append(hit)
    return out
