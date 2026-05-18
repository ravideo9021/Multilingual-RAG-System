"""Tests for the benchmark loader + evaluator.

Strategy:

* JSONL round-trip — write, load, compare.
* Evaluator against a *stub* retriever (no FAISS, no embedder) whose
  returned hits are hand-constructed. That way the test verifies the
  aggregation logic (recall, mrr, ndcg, by_source) without depending on
  any real retrieval stack.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.eval.benchmark import (
    BenchmarkQuery,
    CorpusPassage,
    _hit_doc_id,
    evaluate,
    load_corpus,
    load_queries,
)


# ---------------------------------------------------------------------- #
# Data models + JSONL round-trip
# ---------------------------------------------------------------------- #


class TestBenchmarkQuery:
    def test_from_dict_minimal(self):
        q = BenchmarkQuery.from_dict(
            {
                "qid": "q1",
                "query": "what is x",
                "query_lang": "en",
                "relevant_doc_ids": ["d1", "d2"],
                "source_dataset": "miracl-hi",
            }
        )
        assert q.qid == "q1"
        assert q.query == "what is x"
        assert q.query_lang == "en"
        assert q.relevant_doc_ids == ["d1", "d2"]
        assert q.source_dataset == "miracl-hi"
        assert q.target_lang is None

    def test_from_dict_coerces_relevant_ids_to_str(self):
        """MIRACL mixes int and string doc ids — we normalize on load."""
        q = BenchmarkQuery.from_dict(
            {
                "qid": 42,
                "query": "x",
                "query_lang": "hi",
                "relevant_doc_ids": [1, 2, "three"],
                "source_dataset": "x",
            }
        )
        assert q.qid == "42"
        assert q.relevant_doc_ids == ["1", "2", "three"]


class TestCorpusPassage:
    def test_to_metadata_preserves_doc_id(self):
        """doc_id MUST survive into FAISS metadata so the evaluator can match."""
        p = CorpusPassage(
            doc_id="wiki-123", text="hello", language="en", source="wikipedia", title="T"
        )
        md = p.to_metadata()
        assert md["doc_id"] == "wiki-123"
        assert md["text"] == "hello"
        assert md["language"] == "en"
        assert md["source"] == "wikipedia"
        assert md["title"] == "T"

    def test_from_dict_defaults(self):
        p = CorpusPassage.from_dict({"doc_id": "x", "text": "hello"})
        assert p.language == "unknown"
        assert p.source == ""
        assert p.title == ""


class TestJsonlRoundTrip:
    def test_load_queries(self, tmp_path: Path):
        rows = [
            {
                "qid": "q1",
                "query": "भारत की राजधानी क्या है?",
                "query_lang": "hi",
                "relevant_doc_ids": ["d1"],
                "source_dataset": "miracl-hi",
            },
            {
                "qid": "q2",
                "query": "capital of India",
                "query_lang": "en",
                "target_lang": "hi",
                "relevant_doc_ids": ["d2", "d3"],
                "source_dataset": "xor-tydi",
            },
        ]
        path = tmp_path / "queries.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

        loaded = load_queries(path)
        assert len(loaded) == 2
        assert loaded[0].qid == "q1"
        assert loaded[0].query_lang == "hi"
        assert loaded[1].target_lang == "hi"
        assert loaded[1].source_dataset == "xor-tydi"

    def test_load_corpus(self, tmp_path: Path):
        rows = [
            {"doc_id": "a", "text": "hello", "language": "en", "source": "s"},
            {"doc_id": "b", "text": "नमस्ते", "language": "hi", "source": "s"},
        ]
        path = tmp_path / "corpus.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

        loaded = load_corpus(path)
        assert [p.doc_id for p in loaded] == ["a", "b"]
        assert loaded[1].text == "नमस्ते"
        assert loaded[1].language == "hi"

    def test_load_queries_skips_blank_lines(self, tmp_path: Path):
        path = tmp_path / "queries.jsonl"
        path.write_text(
            '\n{"qid":"q1","query":"x","query_lang":"en","relevant_doc_ids":["d1"],"source_dataset":"t"}\n\n',
            encoding="utf-8",
        )
        loaded = load_queries(path)
        assert len(loaded) == 1
        assert loaded[0].qid == "q1"

    def test_load_queries_reports_line_number_on_error(self, tmp_path: Path):
        path = tmp_path / "bad.jsonl"
        path.write_text(
            '{"qid":"q1","query":"x","query_lang":"en","relevant_doc_ids":["d1"],"source_dataset":"t"}\n'
            "not valid json\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="bad.jsonl:2"):
            load_queries(path)


# ---------------------------------------------------------------------- #
# _hit_doc_id helper
# ---------------------------------------------------------------------- #


class TestHitDocId:
    def test_prefers_doc_id(self):
        assert _hit_doc_id({"doc_id": "wiki-1", "id": 42}) == "wiki-1"

    def test_falls_back_to_id(self):
        """When the hit only has a FAISS int id, we stringify it.
        Matches nothing in a real benchmark but keeps unit tests ergonomic.
        """
        assert _hit_doc_id({"id": 42}) == "42"

    def test_returns_empty_when_neither_present(self):
        assert _hit_doc_id({}) == ""


# ---------------------------------------------------------------------- #
# evaluate() — aggregation against a stub retriever
# ---------------------------------------------------------------------- #


class _StubRetriever:
    """Returns pre-canned hits keyed by query string."""

    def __init__(self, responses: dict[str, list[str]]):
        self._responses = responses
        self.calls: list[tuple[str, int]] = []

    def retrieve(self, query: str, k: int = 5) -> list[dict]:
        self.calls.append((query, k))
        ids = self._responses.get(query, [])
        return [{"doc_id": doc_id, "score": 1.0 - 0.01 * i} for i, doc_id in enumerate(ids)]


def _q(qid: str, query: str, rel: list[str], source: str = "src", lang: str = "en") -> BenchmarkQuery:
    return BenchmarkQuery(
        qid=qid,
        query=query,
        query_lang=lang,
        relevant_doc_ids=rel,
        source_dataset=source,
    )


class TestEvaluate:
    def test_single_hit_at_rank_1(self):
        retriever = _StubRetriever({"q1": ["gold", "x", "y"]})
        queries = [_q("q1", "q1", ["gold"])]
        report = evaluate(retriever, queries)
        assert report.n_queries == 1
        assert report.n_scored == 1
        assert report.recall_at_1 == pytest.approx(1.0)
        assert report.recall_at_5 == pytest.approx(1.0)
        assert report.mrr_at_10 == pytest.approx(1.0)
        assert report.ndcg_at_10 == pytest.approx(1.0)

    def test_miss_gives_zero(self):
        retriever = _StubRetriever({"q1": ["a", "b", "c"]})
        queries = [_q("q1", "q1", ["gold"])]
        report = evaluate(retriever, queries)
        assert report.recall_at_5 == 0.0
        assert report.mrr_at_10 == 0.0
        assert report.ndcg_at_10 == 0.0

    def test_mixed_queries_average(self):
        """2 queries: one hit at rank 1, one miss ⇒ recall@5 = 0.5."""
        retriever = _StubRetriever(
            {
                "q1": ["gold1"],
                "q2": ["x", "y", "z"],
            }
        )
        queries = [
            _q("q1", "q1", ["gold1"]),
            _q("q2", "q2", ["gold2"]),
        ]
        report = evaluate(retriever, queries)
        assert report.n_queries == 2
        assert report.recall_at_5 == pytest.approx(0.5)
        assert report.recall_at_1 == pytest.approx(0.5)

    def test_empty_relevant_ids_skipped_from_mean(self):
        """Query with no gold shouldn't drag the metric down — mean skips Nones."""
        retriever = _StubRetriever(
            {
                "q1": ["gold"],
                "q_nogold": ["whatever"],
            }
        )
        queries = [
            _q("q1", "q1", ["gold"]),
            _q("q_nogold", "q_nogold", []),
        ]
        report = evaluate(retriever, queries)
        assert report.n_queries == 2
        assert report.n_scored == 1
        # Only q1 contributes; its recall is 1.0, so aggregate is 1.0 (not 0.5).
        assert report.recall_at_5 == pytest.approx(1.0)

    def test_by_source_breakdown(self):
        retriever = _StubRetriever(
            {
                "q1": ["g1"],
                "q2": ["x", "y"],  # miss
                "q3": ["g3", "x"],
            }
        )
        queries = [
            _q("q1", "q1", ["g1"], source="miracl-hi"),
            _q("q2", "q2", ["g2"], source="miracl-hi"),
            _q("q3", "q3", ["g3"], source="xor-tydi"),
        ]
        report = evaluate(retriever, queries)
        assert set(report.by_source.keys()) == {"miracl-hi", "xor-tydi"}
        assert report.by_source["miracl-hi"]["n_queries"] == 2
        assert report.by_source["miracl-hi"]["recall_at_5"] == pytest.approx(0.5)
        assert report.by_source["xor-tydi"]["n_queries"] == 1
        assert report.by_source["xor-tydi"]["recall_at_5"] == pytest.approx(1.0)

    def test_retriever_called_with_max_k(self):
        retriever = _StubRetriever({"q1": ["gold"]})
        evaluate(retriever, [_q("q1", "q1", ["gold"])], max_k=10)
        assert retriever.calls == [("q1", 10)]

    def test_max_k_below_10_rejected(self):
        """Dropping max_k below 10 would make @10 metrics silently wrong."""
        retriever = _StubRetriever({})
        with pytest.raises(ValueError, match="max_k"):
            evaluate(retriever, [], max_k=5)

    def test_per_query_records_populated(self):
        retriever = _StubRetriever({"q1": ["gold", "x"]})
        queries = [_q("q1", "q1", ["gold"])]
        report = evaluate(retriever, queries)
        assert len(report.per_query) == 1
        pr = report.per_query[0]
        assert pr.qid == "q1"
        assert pr.retrieved_doc_ids == ["gold", "x"]
        assert pr.n_relevant == 1
        assert pr.recall_at_1 == 1.0

    def test_dataset_name_propagates(self):
        retriever = _StubRetriever({"q1": ["gold"]})
        report = evaluate(
            retriever, [_q("q1", "q1", ["gold"])], dataset_name="custom-name"
        )
        assert report.dataset == "custom-name"
