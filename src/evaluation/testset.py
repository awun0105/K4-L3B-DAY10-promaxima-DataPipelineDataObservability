from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import compact_join, normalize_whitespace, write_json


QUESTION_PLAN = (("summary", 3), ("authors", 3), ("date", 2), ("categories", 2))


def _as_text(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return compact_join(str(item) for item in value)
    if isinstance(value, str):
        value = value.strip()
        if value.startswith("["):
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError:
                pass
            else:
                if isinstance(decoded, list):
                    return compact_join(str(item) for item in decoded)
        return normalize_whitespace(value)
    return "" if pd.isna(value) else normalize_whitespace(str(value))


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build ten real-data benchmark cases consumed by ``evaluate_pipeline``."""
    required = {"paper_id", "title", "summary", "authors", "published", "categories"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Cannot build test set; missing required columns: {', '.join(missing)}")
    if df.empty:
        raise ValueError("Cannot build test set from an empty dataframe.")

    templates = {
        "summary": "What is the summary of '{title}'?", "authors": "Who authored '{title}'?",
        "date": "When was '{title}' published?", "categories": "What categories are listed for '{title}'?",
    }
    value_columns = {"summary": "summary", "authors": "authors", "date": "published", "categories": "categories"}
    cases: list[dict[str, Any]] = []
    for question_type, count in QUESTION_PLAN:
        candidates = df.copy()
        for column in ("paper_id", "title", value_columns[question_type]):
            candidates = candidates.loc[candidates[column].map(_as_text).ne("")]
        if candidates.empty:
            raise ValueError(f"Cannot create {question_type} benchmarks: no complete source record is available.")
        for offset in range(count):
            row = candidates.iloc[offset % len(candidates)]
            title = _as_text(row["title"])
            cases.append({
                "id": f"benchmark-{len(cases) + 1:02d}", "question_type": question_type,
                "question": templates[question_type].format(title=title),
                "ground_truth": _as_text(row[value_columns[question_type]]),
                "ground_truth_doc_ids": [_as_text(row["paper_id"])],
            })
    write_json(Path(output_path), cases)
    return cases
