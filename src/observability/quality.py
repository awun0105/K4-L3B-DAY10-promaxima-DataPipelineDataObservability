from __future__ import annotations

from pathlib import Path
from typing import Any

import great_expectations as gx
import pandas as pd
from great_expectations.expectations import (
    ExpectColumnValueLengthsToBeBetween,
    ExpectColumnValuesToBeUnique,
    ExpectColumnValuesToNotBeNull,
    ExpectTableRowCountToBeBetween,
)

from core.config import Settings
from core.utils import write_json


def _report_path(settings: Settings, report_name: str | Path) -> Path:
    """Resolve a report name without requiring callers to know the quality directory."""
    path = Path(report_name)
    if not path.is_absolute() and path.parent == Path("."):
        path = settings.paths.quality_dir / path
    return path if path.suffix else path.with_suffix(".json")


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run the baseline Great Expectations 1.x quality gate for a papers dataframe."""
    required_columns = {"paper_id", "summary"}
    missing_columns = sorted(required_columns - set(df.columns))
    report: dict[str, Any] = {
        "success": False,
        "row_count": int(len(df)),
        "expectations": [],
        "missing_columns": missing_columns,
    }
    if missing_columns:
        report["error"] = "Required columns are missing; no GX expectations were run."
        write_json(_report_path(settings, report_name), report)
        return report

    # Explicit GX 1.x ephemeral fluent API: no project directory is required.
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})
    expectations = [
        ("table_row_count", ExpectTableRowCountToBeBetween(min_value=15, max_value=50)),
        ("paper_id_not_null", ExpectColumnValuesToNotBeNull(column="paper_id")),
        ("paper_id_unique", ExpectColumnValuesToBeUnique(column="paper_id")),
        ("summary_min_length", ExpectColumnValueLengthsToBeBetween(column="summary", min_value=20)),
    ]
    for name, expectation in expectations:
        result_json = batch.validate(expectation).to_json_dict()
        report["expectations"].append(
            {
                "name": name,
                "success": bool(result_json["success"]),
                "result": result_json.get("result", {}),
                "exception_info": result_json.get("exception_info", {}),
            }
        )
    report["success"] = all(item["success"] for item in report["expectations"])
    write_json(_report_path(settings, report_name), report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Summarize the age-based freshness SLA without silently coercing bad values."""
    total_records = int(len(df))
    report: dict[str, Any] = {
        "total_records": total_records, "stale_records": 0, "stale_ratio": 0.0,
        "is_fresh": True, "stale_threshold_days": 180, "null_age_days": 0, "invalid_age_days": 0,
    }
    if "age_days" not in df.columns:
        report.update({"is_fresh": False, "error": "Required column 'age_days' is missing; freshness cannot be evaluated."})
        write_json(Path(report_path), report)
        return report

    numeric_age = pd.to_numeric(df["age_days"], errors="coerce")
    original_null = df["age_days"].isna()
    invalid = numeric_age.isna() & ~original_null
    report["null_age_days"] = int(original_null.sum())
    report["invalid_age_days"] = int(invalid.sum())
    report["stale_records"] = int((numeric_age > 180).sum())
    report["stale_ratio"] = report["stale_records"] / total_records if total_records else 0.0
    # Unknown ages prevent claiming that the data meets its SLA.
    report["is_fresh"] = bool(report["stale_ratio"] <= 0.25 and not report["null_age_days"] and not report["invalid_age_days"])
    if "published" in df.columns:
        published = pd.to_datetime(df["published"], errors="coerce", utc=True).dropna()
        report["latest_published"] = published.max().date().isoformat() if not published.empty else None
        report["oldest_published"] = published.min().date().isoformat() if not published.empty else None
    write_json(Path(report_path), report)
    return report
