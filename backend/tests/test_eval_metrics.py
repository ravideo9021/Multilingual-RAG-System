"""Tests for retrieval metrics.

All expected values are hand-verified so a failure points at a logic
bug rather than a bad golden number.

Conventions recap:
    recall@k — 1.0 if any relevant id appears in top-k, else 0.0.
    mrr@k   — 1/rank of first relevant in top-k; 0.0 if none; rank is 1-indexed.
    ndcg@k  — sum(1/log2(rank+1)) normalized by ideal.
    mean    — arithmetic mean, skipping None (so empty-relevant queries don't bias).

All four return None when relevant_ids is empty — caller aggregates by
skipping those.
"""

from __future__ import annotations

import math

import pytest

from app.eval.metrics import mean, mrr_at_k, ndcg_at_k, recall_at_k


# ---------------------------------------------------------------------- #
# recall_at_k
# ---------------------------------------------------------------------- #


class TestRecallAtK:
    def test_hit_at_rank_1(self):
        assert recall_at_k(["gold"], ["gold", "x", "y"], k=1) == 1.0

    def test_hit_at_rank_5_but_not_rank_1(self):
        retrieved = ["a", "b", "c", "d", "gold"]
        assert recall_at_k(["gold"], retrieved, k=5) == 1.0
        assert recall_at_k(["gold"], retrieved, k=4) == 0.0

    def test_miss_returns_zero(self):
        assert recall_at_k(["gold"], ["a", "b", "c"], k=3) == 0.0

    def test_multiple_relevant_any_hit(self):
        """Binary recall — one hit out of many relevants still scores 1.0."""
        assert recall_at_k(["g1", "g2", "g3"], ["x", "g2", "y"], k=5) == 1.0

    def test_empty_relevant_returns_none(self):
        """No gold ⇒ not scorable; mean() skips Nones."""
        assert recall_at_k([], ["a", "b"], k=5) is None

    def test_empty_retrieved_returns_zero(self):
        assert recall_at_k(["gold"], [], k=5) == 0.0

    def test_k_must_be_positive(self):
        with pytest.raises(ValueError):
            recall_at_k(["gold"], ["a"], k=0)
        with pytest.raises(ValueError):
            recall_at_k(["gold"], ["a"], k=-3)

    def test_exact_k_boundary(self):
        """Item at exactly rank k counts; rank k+1 does not."""
        retrieved = [f"r{i}" for i in range(10)]
        retrieved.append("gold")  # rank 11
        assert recall_at_k(["gold"], retrieved, k=10) == 0.0
        assert recall_at_k(["gold"], retrieved, k=11) == 1.0


# ---------------------------------------------------------------------- #
# mrr_at_k
# ---------------------------------------------------------------------- #


class TestMRRAtK:
    def test_rank_1_gives_one(self):
        assert mrr_at_k(["gold"], ["gold"], k=10) == pytest.approx(1.0)

    def test_rank_2_gives_half(self):
        assert mrr_at_k(["gold"], ["x", "gold"], k=10) == pytest.approx(0.5)

    def test_rank_3_gives_third(self):
        assert mrr_at_k(["gold"], ["x", "y", "gold"], k=10) == pytest.approx(1 / 3)

    def test_first_relevant_wins(self):
        """MRR cares about the EARLIEST relevant — later ones don't count."""
        retrieved = ["x", "g1", "y", "g2"]
        # g1 at rank 2 → 1/2, not 1/4
        assert mrr_at_k(["g1", "g2"], retrieved, k=10) == pytest.approx(0.5)

    def test_miss_in_topk_returns_zero(self):
        assert mrr_at_k(["gold"], ["a", "b", "c"], k=3) == 0.0

    def test_relevant_past_k_returns_zero(self):
        retrieved = [f"r{i}" for i in range(10)] + ["gold"]
        assert mrr_at_k(["gold"], retrieved, k=10) == 0.0

    def test_empty_relevant_returns_none(self):
        assert mrr_at_k([], ["a"], k=5) is None

    def test_k_must_be_positive(self):
        with pytest.raises(ValueError):
            mrr_at_k(["gold"], ["a"], k=0)


# ---------------------------------------------------------------------- #
# ndcg_at_k
# ---------------------------------------------------------------------- #


class TestNDCGAtK:
    def test_perfect_ranking_is_one(self):
        """All relevants at the top ⇒ nDCG = 1.0."""
        assert ndcg_at_k(["g1", "g2"], ["g1", "g2", "x", "y"], k=5) == pytest.approx(1.0)

    def test_single_relevant_at_rank_1(self):
        # DCG = 1/log2(2) = 1.0; IDCG = 1.0 → nDCG = 1.0
        assert ndcg_at_k(["gold"], ["gold", "x"], k=5) == pytest.approx(1.0)

    def test_single_relevant_at_rank_2(self):
        # DCG = 1/log2(3); IDCG = 1/log2(2) = 1.0 → 1/log2(3)
        expected = 1.0 / math.log2(3)
        assert ndcg_at_k(["gold"], ["x", "gold"], k=5) == pytest.approx(expected)

    def test_two_relevants_out_of_order(self):
        """Known case: 2 relevants at ranks 2 and 4 ⇒
        DCG = 1/log2(3) + 1/log2(5);
        IDCG = 1/log2(2) + 1/log2(3) = 1 + 1/log2(3).
        """
        retrieved = ["x", "g1", "y", "g2", "z"]
        dcg = 1.0 / math.log2(3) + 1.0 / math.log2(5)
        idcg = 1.0 + 1.0 / math.log2(3)
        assert ndcg_at_k(["g1", "g2"], retrieved, k=5) == pytest.approx(dcg / idcg)

    def test_no_relevants_in_topk(self):
        assert ndcg_at_k(["gold"], ["a", "b", "c"], k=3) == 0.0

    def test_empty_relevant_returns_none(self):
        assert ndcg_at_k([], ["a"], k=5) is None

    def test_idcg_caps_at_k(self):
        """More relevants than k ⇒ IDCG is computed at k positions (not len(rel))."""
        # 5 relevants, k=2 → IDCG = 1 + 1/log2(3). If retrieval puts 2 relevants
        # in top-2 in order, nDCG should be 1.0, not less.
        rel = ["g1", "g2", "g3", "g4", "g5"]
        retrieved = ["g1", "g2", "x", "y"]
        assert ndcg_at_k(rel, retrieved, k=2) == pytest.approx(1.0)

    def test_k_must_be_positive(self):
        with pytest.raises(ValueError):
            ndcg_at_k(["gold"], ["a"], k=0)


# ---------------------------------------------------------------------- #
# mean
# ---------------------------------------------------------------------- #


class TestMean:
    def test_basic_mean(self):
        assert mean([1.0, 2.0, 3.0]) == pytest.approx(2.0)

    def test_skips_none(self):
        # Average of 1.0 and 3.0, not 1.0 + 0 + 3.0 / 3.
        assert mean([1.0, None, 3.0]) == pytest.approx(2.0)

    def test_all_none_returns_zero(self):
        assert mean([None, None]) == 0.0

    def test_empty_returns_zero(self):
        assert mean([]) == 0.0

    def test_zeros_included(self):
        """0.0 is a legit metric value — it must NOT be treated like None."""
        assert mean([0.0, 0.0, 1.0]) == pytest.approx(1 / 3)
