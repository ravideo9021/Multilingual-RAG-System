"""Report writer — turns evaluation reports into markdown + JSON files.

Two output formats:

* **Markdown** (``REPORT.md``) — human-readable, with placeholder strings
  for any metric the user hasn't supplied real numbers for yet. This
  file is the one committed to the repo and shown in the README.
* **JSON** (``eval_results/*.json``) — the raw report, suitable for
  re-reading programmatically, diffing across runs, or posting to a
  dashboard.

The placeholder string ``<TO_BE_FILLED_BY_RUNNER: ...>`` appears wherever
a metric hasn't been computed yet. This is deliberate — the project
policy is that benchmark numbers are never faked, so any markdown produced
before the user runs the full eval keeps placeholders visible in the
repo until real numbers land.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.eval.benchmark import BenchmarkReport
from app.eval.embedding_compare import ComparisonReport

logger = logging.getLogger(__name__)

PLACEHOLDER = "<TO_BE_FILLED_BY_RUNNER>"


def _fmt_metric(value: float | None) -> str:
    """Format a metric for markdown. Falls back to a placeholder if None."""
    if value is None:
        return PLACEHOLDER
    return f"{value:.3f}"


def render_markdown(
    *,
    title: str,
    comparison: ComparisonReport | None = None,
    single_report: BenchmarkReport | None = None,
    notes: str | None = None,
    generated_at: str | None = None,
) -> str:
    """Render an evaluation summary as markdown.

    Exactly one of ``comparison`` or ``single_report`` should be provided
    (or neither — in which case the report is a template with
    placeholders).
    """
    if generated_at is None:
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = [f"# {title}", "", f"_Generated: {generated_at}_", ""]

    if comparison is not None:
        lines.append("## Embedding comparison")
        lines.append("")
        lines.append(f"Benchmark: **{comparison.dataset}** ({comparison.n_queries} queries)")
        lines.append("")
        lines.append("| Embedder | Recall@1 | Recall@5 | Recall@10 | MRR@10 | nDCG@10 |")
        lines.append("|---|---|---|---|---|---|")
        for name, r in comparison.per_embedder.items():
            lines.append(
                "| {e} | {r1} | {r5} | {r10} | {mrr} | {ndcg} |".format(
                    e=name,
                    r1=_fmt_metric(r.recall_at_1),
                    r5=_fmt_metric(r.recall_at_5),
                    r10=_fmt_metric(r.recall_at_10),
                    mrr=_fmt_metric(r.mrr_at_10),
                    ndcg=_fmt_metric(r.ndcg_at_10),
                )
            )
        lines.append("")

    if single_report is not None:
        lines.append(f"## {single_report.dataset}")
        lines.append("")
        lines.append(f"Queries: **{single_report.n_queries}** "
                     f"({single_report.n_scored} with gold labels)")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|---|---|")
        lines.append(f"| Recall@1 | {_fmt_metric(single_report.recall_at_1)} |")
        lines.append(f"| Recall@5 | {_fmt_metric(single_report.recall_at_5)} |")
        lines.append(f"| Recall@10 | {_fmt_metric(single_report.recall_at_10)} |")
        lines.append(f"| MRR@10 | {_fmt_metric(single_report.mrr_at_10)} |")
        lines.append(f"| nDCG@10 | {_fmt_metric(single_report.ndcg_at_10)} |")
        lines.append("")
        if single_report.by_source:
            lines.append("### By sub-dataset")
            lines.append("")
            lines.append("| Sub-dataset | N | Recall@5 | Recall@10 | MRR@10 | nDCG@10 |")
            lines.append("|---|---|---|---|---|---|")
            for src, m in single_report.by_source.items():
                lines.append(
                    "| {s} | {n} | {r5} | {r10} | {mrr} | {ndcg} |".format(
                        s=src,
                        n=int(m.get("n_queries", 0)),
                        r5=_fmt_metric(m.get("recall_at_5")),
                        r10=_fmt_metric(m.get("recall_at_10")),
                        mrr=_fmt_metric(m.get("mrr_at_10")),
                        ndcg=_fmt_metric(m.get("ndcg_at_10")),
                    )
                )
            lines.append("")

    if notes:
        lines.append("## Notes")
        lines.append("")
        lines.append(notes)
        lines.append("")

    return "\n".join(lines)


def write_markdown(path: str | Path, markdown: str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    logger.info("Wrote markdown report to %s", path)
    return path


def write_json(path: str | Path, report: BenchmarkReport | ComparisonReport) -> Path:
    """Dump a report (with per-query detail) as JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(report, BenchmarkReport):
        payload = {
            **report.to_summary_dict(),
            "per_query": [asdict(r) for r in report.per_query],
        }
    else:  # ComparisonReport
        payload = {
            "dataset": report.dataset,
            "n_queries": report.n_queries,
            "per_embedder": {
                name: {
                    **r.to_summary_dict(),
                    "per_query": [asdict(pr) for pr in r.per_query],
                }
                for name, r in report.per_embedder.items()
            },
        }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Wrote JSON report to %s", path)
    return path
