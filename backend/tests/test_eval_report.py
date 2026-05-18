"""Tests for the markdown + JSON report writers.

The central invariant under test: when a metric is ``None`` (unmeasured),
the rendered markdown contains the ``<TO_BE_FILLED_BY_RUNNER>`` placeholder
rather than a fabricated number. The project policy is that benchmark
numbers are never faked, and this placeholder is how that policy is
enforced at the output layer.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.eval.benchmark import BenchmarkReport, PerQueryResult
from app.eval.embedding_compare import ComparisonReport
from app.eval.report import (
    PLACEHOLDER,
    _fmt_metric,
    render_markdown,
    write_json,
    write_markdown,
)


# ---------------------------------------------------------------------- #
# _fmt_metric
# ---------------------------------------------------------------------- #


class TestFmtMetric:
    def test_none_becomes_placeholder(self):
        assert _fmt_metric(None) == PLACEHOLDER

    def test_float_formats_to_three_decimals(self):
        assert _fmt_metric(0.8) == "0.800"
        assert _fmt_metric(0.12345) == "0.123"

    def test_zero_is_not_placeholder(self):
        """0.0 is a real measured value — it must render as a number."""
        assert _fmt_metric(0.0) == "0.000"


# ---------------------------------------------------------------------- #
# Fixtures
# ---------------------------------------------------------------------- #


def _make_report(dataset: str = "demo", **overrides) -> BenchmarkReport:
    defaults = dict(
        dataset=dataset,
        n_queries=10,
        n_scored=8,
        recall_at_1=0.5,
        recall_at_5=0.8,
        recall_at_10=0.9,
        mrr_at_10=0.6,
        ndcg_at_10=0.7,
        per_query=[
            PerQueryResult(
                qid="q1",
                query_lang="en",
                source_dataset="miracl-hi",
                n_relevant=1,
                retrieved_doc_ids=["gold"],
                recall_at_1=1.0,
                recall_at_5=1.0,
                recall_at_10=1.0,
                mrr_at_10=1.0,
                ndcg_at_10=1.0,
            )
        ],
        by_source={
            "miracl-hi": {
                "n_queries": 5,
                "recall_at_5": 0.8,
                "recall_at_10": 0.9,
                "mrr_at_10": 0.6,
                "ndcg_at_10": 0.7,
            }
        },
    )
    defaults.update(overrides)
    return BenchmarkReport(**defaults)


# ---------------------------------------------------------------------- #
# render_markdown — single_report
# ---------------------------------------------------------------------- #


class TestRenderSingleReport:
    def test_title_and_metadata_present(self):
        md = render_markdown(
            title="Demo eval",
            single_report=_make_report(),
            generated_at="2026-01-01 00:00 UTC",
        )
        assert "# Demo eval" in md
        assert "_Generated: 2026-01-01 00:00 UTC_" in md

    def test_metrics_formatted(self):
        md = render_markdown(title="t", single_report=_make_report())
        assert "| Recall@1 | 0.500 |" in md
        assert "| Recall@5 | 0.800 |" in md
        assert "| MRR@10 | 0.600 |" in md

    def test_query_counts_present(self):
        md = render_markdown(title="t", single_report=_make_report())
        assert "10" in md
        assert "8 with gold labels" in md

    def test_by_source_section_rendered(self):
        md = render_markdown(title="t", single_report=_make_report())
        assert "### By sub-dataset" in md
        assert "| miracl-hi |" in md

    def test_notes_appended_when_provided(self):
        md = render_markdown(
            title="t",
            single_report=_make_report(),
            notes="Mini benchmark — scaled down from full MIRACL-hi.",
        )
        assert "## Notes" in md
        assert "scaled down" in md


# ---------------------------------------------------------------------- #
# render_markdown — comparison
# ---------------------------------------------------------------------- #


class TestRenderComparison:
    def test_comparison_table_has_one_row_per_embedder(self):
        cmp = ComparisonReport(dataset="d", n_queries=10)
        cmp.per_embedder["bge-m3"] = _make_report(dataset="d")
        cmp.per_embedder["e5"] = _make_report(
            dataset="d", recall_at_5=0.7, mrr_at_10=0.55, ndcg_at_10=0.65
        )
        md = render_markdown(title="comparison", comparison=cmp)
        # Header + separator + 2 rows = 4 lines containing "|"
        table_lines = [line for line in md.splitlines() if line.startswith("|")]
        assert len(table_lines) == 2 + 2  # header + sep + 2 embedders
        assert "bge-m3" in md
        assert "e5" in md
        assert "0.800" in md
        assert "0.700" in md

    def test_dataset_and_query_count_rendered(self):
        cmp = ComparisonReport(dataset="miracl-hi+xortydi", n_queries=42)
        md = render_markdown(title="t", comparison=cmp)
        assert "miracl-hi+xortydi" in md
        assert "42 queries" in md


# ---------------------------------------------------------------------- #
# Placeholder behavior — the invariant that prevents faked numbers
# ---------------------------------------------------------------------- #


class TestPlaceholderInvariant:
    def test_none_metrics_render_as_placeholder_in_single_report(self):
        """If the report is constructed with None metrics (e.g., a template),
        the markdown shows <TO_BE_FILLED_BY_RUNNER>, not a fake number."""
        report = BenchmarkReport(
            dataset="d",
            n_queries=0,
            n_scored=0,
            recall_at_1=None,  # type: ignore[arg-type]
            recall_at_5=None,  # type: ignore[arg-type]
            recall_at_10=None,  # type: ignore[arg-type]
            mrr_at_10=None,  # type: ignore[arg-type]
            ndcg_at_10=None,  # type: ignore[arg-type]
        )
        md = render_markdown(title="t", single_report=report)
        assert md.count(PLACEHOLDER) >= 5

    def test_none_metrics_render_as_placeholder_in_comparison(self):
        cmp = ComparisonReport(dataset="d", n_queries=0)
        cmp.per_embedder["unmeasured"] = BenchmarkReport(
            dataset="d",
            n_queries=0,
            n_scored=0,
            recall_at_1=None,  # type: ignore[arg-type]
            recall_at_5=None,  # type: ignore[arg-type]
            recall_at_10=None,  # type: ignore[arg-type]
            mrr_at_10=None,  # type: ignore[arg-type]
            ndcg_at_10=None,  # type: ignore[arg-type]
        )
        md = render_markdown(title="t", comparison=cmp)
        # One row × 5 placeholder metric cells.
        assert md.count(PLACEHOLDER) == 5


# ---------------------------------------------------------------------- #
# write_markdown / write_json
# ---------------------------------------------------------------------- #


class TestWriteMarkdown:
    def test_writes_file(self, tmp_path: Path):
        out = tmp_path / "nested" / "REPORT.md"
        write_markdown(out, "# hello")
        assert out.read_text(encoding="utf-8") == "# hello"

    def test_creates_parent_dirs(self, tmp_path: Path):
        out = tmp_path / "a" / "b" / "c" / "REPORT.md"
        write_markdown(out, "x")
        assert out.exists()


class TestWriteJson:
    def test_single_report_json_roundtrip(self, tmp_path: Path):
        out = tmp_path / "single.json"
        report = _make_report()
        write_json(out, report)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["dataset"] == "demo"
        assert data["n_queries"] == 10
        assert data["recall_at_5"] == 0.8
        assert len(data["per_query"]) == 1
        assert data["per_query"][0]["qid"] == "q1"
        assert data["by_source"]["miracl-hi"]["n_queries"] == 5

    def test_comparison_report_json_roundtrip(self, tmp_path: Path):
        cmp = ComparisonReport(dataset="d", n_queries=10)
        cmp.per_embedder["bge-m3"] = _make_report(dataset="d")
        cmp.per_embedder["e5"] = _make_report(dataset="d", recall_at_5=0.7)

        out = tmp_path / "compare.json"
        write_json(out, cmp)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["dataset"] == "d"
        assert set(data["per_embedder"].keys()) == {"bge-m3", "e5"}
        assert data["per_embedder"]["bge-m3"]["recall_at_5"] == 0.8
        assert data["per_embedder"]["e5"]["recall_at_5"] == 0.7
        assert "per_query" in data["per_embedder"]["bge-m3"]

    def test_unicode_preserved(self, tmp_path: Path):
        """ensure_ascii=False must be used so Devanagari survives JSON."""
        report = _make_report()
        report.per_query[0].retrieved_doc_ids = ["भारत"]
        out = tmp_path / "u.json"
        write_json(out, report)
        assert "भारत" in out.read_text(encoding="utf-8")
