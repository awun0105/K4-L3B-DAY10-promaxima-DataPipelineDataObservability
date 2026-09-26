from __future__ import annotations

from typing import Any

from core.utils import write_text


def _value(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if value is None:
        return "Not available (artifact dependency not supplied)"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _first_value(payload: dict[str, Any], *keys: str) -> str:
    for key in keys:
        if payload.get(key) is not None:
            return _value(payload, key)
    return "Not available (artifact dependency not supplied)"


def _markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _quality_status(quality: dict[str, Any]) -> str:
    if "success" not in quality:
        return "Not available (artifact dependency not supplied)"
    return "PASS" if quality["success"] else "FAIL"


def _freshness_status(freshness: dict[str, Any]) -> str:
    if "is_fresh" not in freshness:
        return "Not available (artifact dependency not supplied)"
    return "FRESH" if freshness["is_fresh"] else "STALE / UNVERIFIED"


def _numeric(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Create a baseline report strictly from the supplied pipeline artifacts."""
    lines = [
        "# Phase 1 Data Pipeline Report", "", "## Dataset / Data Quality", "",
        f"- Source: {_first_value(source_summary, 'source', 'source_api')}",
        f"- Records: {_first_value(source_summary, 'records', 'clean_rows', 'total_records')}",
        f"- Quality gate: {_quality_status(quality)}",
        f"- Quality report error: {_value(quality, 'error')}", "", "## Freshness", "",
        f"- Status: {_freshness_status(freshness)}",
        f"- Total records: {_value(freshness, 'total_records')}",
        f"- Stale records: {_value(freshness, 'stale_records')}",
        f"- Stale ratio: {_value(freshness, 'stale_ratio')}", "", "## Evaluation Metrics", "",
        f"- Retrieval hit rate: {_value(metrics, 'retrieval_hit_rate')}",
        f"- Mean token F1: {_value(metrics, 'mean_token_f1')}",
        f"- Judge accuracy: {_value(metrics, 'judge_accuracy')}",
        f"- Mean judge score: {_value(metrics, 'mean_judge_score')}", "", "## Evidence-based Assessment", "",
    ]
    if "success" in quality and "is_fresh" in freshness:
        if quality["success"] and freshness["is_fresh"]:
            lines.append("The supplied artifacts indicate that the quality gate passed and freshness SLA was met.")
        else:
            lines.append("The supplied artifacts indicate that at least one data gate did not pass; inspect the linked JSON artifacts before release.")
    else:
        lines.append("Assessment is pending because one or more pipeline artifacts were not supplied.")
    write_text(report_path, "\n".join(lines) + "\n")


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Create the corruption comparison report without inventing absent measurements."""
    metric_names = ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score")
    lines = [
        "# Corruption and Recovery Report", "", "## Baseline vs Corrupted vs Repaired", "",
        "| Metric | Baseline | Corrupted | Repaired |", "| --- | --- | --- | --- |",
    ]
    for metric in metric_names:
        lines.append(
            f"| {metric} | {_markdown_cell(_value(baseline_metrics, metric))} | "
            f"{_markdown_cell(_value(corrupted_metrics, metric))} | {_markdown_cell(_value(repaired_metrics, metric))} |"
        )

    lines.extend([
        "", "## Data Quality", "",
        f"- Corrupted quality gate: {_quality_status(corrupted_quality)}",
        f"- Repaired quality gate: {_quality_status(repaired_quality)}", "", "## Freshness", "",
        f"- Corrupted freshness: {_freshness_status(corrupted_freshness)}",
        f"- Repaired freshness: {_freshness_status(repaired_freshness)}", "", "## Degradation and Recovery", "",
    ])
    baseline_f1 = _numeric(baseline_metrics.get("mean_token_f1"))
    corrupted_f1 = _numeric(corrupted_metrics.get("mean_token_f1"))
    repaired_f1 = _numeric(repaired_metrics.get("mean_token_f1"))
    if baseline_f1 is not None and corrupted_f1 is not None:
        lines.append(f"- Mean token F1 change after corruption: {corrupted_f1 - baseline_f1:+.4f}.")
    else:
        lines.append("- Degradation analysis pending: baseline and corrupted evaluation artifacts are required.")
    if corrupted_f1 is not None and repaired_f1 is not None:
        lines.append(f"- Mean token F1 recovery after repair: {repaired_f1 - corrupted_f1:+.4f}.")
    else:
        lines.append("- Recovery analysis pending: corrupted and repaired evaluation artifacts are required.")
    write_text(report_path, "\n".join(lines) + "\n")
