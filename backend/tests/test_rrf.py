"""Tests for Reciprocal Rank Fusion.

Every test uses hand-constructed ranked lists where the expected fused
scores can be computed by hand:

    rrf(doc, k) = sum over lists of 1 / (k + rank_1_indexed)
"""

from __future__ import annotations

import pytest

from app.retrieval.rrf import reciprocal_rank_fusion


class TestBasicMath:
    def test_single_list_preserves_order(self):
        """With one input list, RRF must preserve rank order."""
        lst = [
            {"id": "a", "score": 0.9},
            {"id": "b", "score": 0.8},
            {"id": "c", "score": 0.7},
        ]
        fused = reciprocal_rank_fusion([lst], k=60)
        assert [h["id"] for h in fused] == ["a", "b", "c"]
        # Scores are 1/(60+1), 1/(60+2), 1/(60+3)
        assert fused[0]["score"] == pytest.approx(1 / 61)
        assert fused[1]["score"] == pytest.approx(1 / 62)
        assert fused[2]["score"] == pytest.approx(1 / 63)

    def test_two_lists_disjoint(self):
        """Two lists with no overlap — each doc gets its single contribution."""
        l1 = [{"id": "a"}, {"id": "b"}]
        l2 = [{"id": "c"}, {"id": "d"}]
        fused = reciprocal_rank_fusion([l1, l2], k=60)
        assert len(fused) == 4
        # Order: a (rank 1 in l1), c (rank 1 in l2) tie at 1/61; b and d tie at 1/62.
        # Tiebreak by first-seen → a, c, b, d.
        assert [h["id"] for h in fused] == ["a", "c", "b", "d"]

    def test_shared_doc_gets_boosted(self):
        """A doc appearing in multiple lists outranks a doc in only one."""
        l1 = [{"id": "shared"}, {"id": "a"}, {"id": "b"}]
        l2 = [{"id": "shared"}, {"id": "c"}, {"id": "d"}]
        fused = reciprocal_rank_fusion([l1, l2], k=60)
        assert fused[0]["id"] == "shared"
        # shared: 2 * 1/61; a/b/c/d: 1/62, 1/63, 1/62, 1/63
        assert fused[0]["score"] == pytest.approx(2 / 61)

    def test_same_doc_different_ranks(self):
        """A doc at rank 1 in one list and rank 5 in another — verify the math."""
        l1 = [{"id": "x"}, {"id": "y"}]
        l2 = [{"id": "y"}, {"id": "z"}, {"id": "w"}, {"id": "v"}, {"id": "x"}]
        fused = reciprocal_rank_fusion([l1, l2], k=60)
        # x: 1/(60+1) + 1/(60+5) = 1/61 + 1/65
        # y: 1/(60+2) + 1/(60+1) = 1/62 + 1/61
        # z: 1/62, w: 1/63, v: 1/64
        expected_x = 1 / 61 + 1 / 65
        expected_y = 1 / 62 + 1 / 61
        by_id = {h["id"]: h["score"] for h in fused}
        assert by_id["x"] == pytest.approx(expected_x)
        assert by_id["y"] == pytest.approx(expected_y)
        # y edges out x because of its better average rank.
        assert fused[0]["id"] == "y"

    def test_k_damping_affects_spread(self):
        """A larger k flattens the score gap between top and bottom."""
        lst = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        low_k = reciprocal_rank_fusion([lst], k=1)
        high_k = reciprocal_rank_fusion([lst], k=1000)
        low_ratio = low_k[0]["score"] / low_k[-1]["score"]
        high_ratio = high_k[0]["score"] / high_k[-1]["score"]
        # With k=1:  1/2 vs 1/4 → ratio 2
        # With k=1000: 1/1001 vs 1/1003 → ratio ~1.002
        assert low_ratio > high_ratio


class TestEdgeCases:
    def test_empty_outer_list(self):
        assert reciprocal_rank_fusion([]) == []

    def test_all_empty_inner_lists(self):
        assert reciprocal_rank_fusion([[], [], []]) == []

    def test_one_empty_list_among_others(self):
        l1 = [{"id": "a"}]
        fused = reciprocal_rank_fusion([l1, [], [{"id": "a"}]], k=60)
        # 'a' appears in two non-empty lists, both at rank 1.
        assert len(fused) == 1
        assert fused[0]["score"] == pytest.approx(2 / 61)

    def test_top_k_truncation(self):
        lst = [{"id": f"d{i}"} for i in range(10)]
        fused = reciprocal_rank_fusion([lst], k=60, top_k=3)
        assert len(fused) == 3
        assert [h["id"] for h in fused] == ["d0", "d1", "d2"]

    def test_top_k_none_returns_all(self):
        lst = [{"id": f"d{i}"} for i in range(10)]
        fused = reciprocal_rank_fusion([lst], k=60, top_k=None)
        assert len(fused) == 10

    def test_k_less_than_one_raises(self):
        with pytest.raises(ValueError, match="k must be"):
            reciprocal_rank_fusion([[{"id": "a"}]], k=0)

    def test_missing_id_raises(self):
        with pytest.raises(KeyError, match="id"):
            reciprocal_rank_fusion([[{"score": 0.9}]], k=60)


class TestMetadataPreservation:
    def test_first_seen_metadata_wins(self):
        """When a doc appears in multiple lists, metadata from the first list wins."""
        l1 = [{"id": "x", "text": "first", "source": "doc1"}]
        l2 = [{"id": "x", "text": "second", "source": "doc2"}]
        fused = reciprocal_rank_fusion([l1, l2], k=60)
        assert fused[0]["text"] == "first"
        assert fused[0]["source"] == "doc1"
        # But the score is the fused sum.
        assert fused[0]["score"] == pytest.approx(2 / 61)

    def test_input_not_mutated(self):
        """RRF must not overwrite the 'score' on input dicts."""
        original = {"id": "a", "score": 0.99}
        l1 = [original]
        reciprocal_rank_fusion([l1], k=60)
        assert original["score"] == 0.99

    def test_extra_fields_preserved(self):
        l1 = [{"id": "a", "language": "hi", "extra": 42}]
        fused = reciprocal_rank_fusion([l1], k=60)
        assert fused[0]["language"] == "hi"
        assert fused[0]["extra"] == 42
