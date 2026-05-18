"""Tests for :func:`app.retrieval.threshold.apply_threshold`."""

from __future__ import annotations

from app.retrieval.threshold import apply_threshold


def test_exactly_at_threshold_is_kept():
    hits = [{"id": 1, "score": 0.35}]
    assert apply_threshold(hits, 0.35) == hits


def test_just_below_threshold_is_dropped():
    hits = [{"id": 1, "score": 0.349}]
    assert apply_threshold(hits, 0.35) == []


def test_just_above_threshold_is_kept():
    hits = [{"id": 1, "score": 0.351}]
    assert apply_threshold(hits, 0.35) == hits


def test_empty_input_returns_empty():
    assert apply_threshold([], 0.35) == []


def test_all_below_threshold_returns_empty():
    hits = [{"id": i, "score": 0.1} for i in range(5)]
    assert apply_threshold(hits, 0.5) == []


def test_all_above_threshold_returns_all():
    hits = [{"id": i, "score": 0.9 - i * 0.01} for i in range(5)]
    assert apply_threshold(hits, 0.5) == hits


def test_mixed_filters_correctly():
    hits = [
        {"id": 1, "score": 0.9},
        {"id": 2, "score": 0.4},  # below 0.5
        {"id": 3, "score": 0.6},
        {"id": 4, "score": 0.2},  # below
    ]
    kept = apply_threshold(hits, 0.5)
    assert [h["id"] for h in kept] == [1, 3]


def test_preserves_order():
    """Threshold filter must preserve input order (assumed best-to-worst)."""
    hits = [
        {"id": 1, "score": 0.9},
        {"id": 2, "score": 0.8},
        {"id": 3, "score": 0.7},
    ]
    kept = apply_threshold(hits, 0.5)
    assert [h["id"] for h in kept] == [1, 2, 3]


def test_hit_without_score_is_dropped():
    hits = [
        {"id": 1, "score": 0.9},
        {"id": 2},  # missing score
        {"id": 3, "score": 0.8},
    ]
    kept = apply_threshold(hits, 0.5)
    assert [h["id"] for h in kept] == [1, 3]


def test_zero_threshold_keeps_positive_scores():
    hits = [
        {"id": 1, "score": 0.1},
        {"id": 2, "score": 0.0},
        {"id": 3, "score": -0.1},
    ]
    kept = apply_threshold(hits, 0.0)
    assert [h["id"] for h in kept] == [1, 2]


def test_negative_threshold_keeps_everything_in_range():
    hits = [
        {"id": 1, "score": 0.5},
        {"id": 2, "score": -0.3},
        {"id": 3, "score": -0.9},
    ]
    kept = apply_threshold(hits, -0.5)
    assert [h["id"] for h in kept] == [1, 2]
