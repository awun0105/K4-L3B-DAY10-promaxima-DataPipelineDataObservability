from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

import pandas as pd

from ingestion.cleaning import format_text_for_embedding


def corrupt_clean_dataframe(
    df: pd.DataFrame,
    output_log_path: Path | str | None = None,
) -> pd.DataFrame:
    """Simulate 6 kịch bản data corruption cho RAG & Observability.

    6 kịch bản tiêm lỗi theo kế hoạch chuẩn (plan.md CP4):
    1. Drop latest records: Xóa 20% bản ghi mới nhất theo ngày xuất bản (mất thông tin truy vấn).
    2. Blank summary: Xóa rỗng trường summary của 2 bản ghi (vi phạm độ dài tối thiểu summary).
    3. Inject noise: Chèn chuỗi ký tự rác vào summary của 2 bản ghi (gây suy giảm ngữ nghĩa).
    4. Truncate title: Cắt ngắn tiêu đề xuống < 8 ký tự cho 2 bản ghi (hỏng exact title lookup).
    5. Stale date: Lùi ngày xuất bản về quá khứ 5 năm cho 6 bản ghi (vi phạm Freshness SLA > 25% stale).
    6. Duplicate rows: Nhân bản 2 dòng có sẵn (vi phạm tính duy nhất của paper_id).

    Rebuild lại `text_for_embedding`, `summary_chars`, `age_days`.
    Ghi nhật ký chi tiết vào `output_log_path` (mặc định data/results/corruption_log.json).
    """
    if df.empty:
        return df.copy()

    corrupted = df.copy()
    original_count = len(corrupted)
    log_entries: list[dict[str, Any]] = []

    # 1. Drop latest records (20% bản ghi mới nhất)
    corrupted_sorted = corrupted.sort_values(by="published", ascending=False)
    num_to_drop = max(1, int(len(corrupted) * 0.20))
    dropped_slice = corrupted_sorted.iloc[:num_to_drop]
    dropped_info = [
        {"paper_id": str(row["paper_id"]), "title": str(row["title"]), "published": str(row["published"])}
        for _, row in dropped_slice.iterrows()
    ]
    corrupted = corrupted.drop(index=dropped_slice.index).reset_index(drop=True)
    log_entries.append(
        {
            "scenario": 1,
            "type": "drop_latest_records",
            "description": f"Xóa {num_to_drop} bản ghi mới nhất theo ngày xuất bản (20% corpus)",
            "affected_count": num_to_drop,
            "affected_records": dropped_info,
        }
    )

    # 2. Blank summary (2 bản ghi đầu tiên)
    blank_indices = [0, 1] if len(corrupted) >= 2 else list(range(len(corrupted)))
    blanked_info = []
    for idx in blank_indices:
        blanked_info.append(
            {
                "paper_id": str(corrupted.loc[idx, "paper_id"]),
                "original_summary_len": len(str(corrupted.loc[idx, "summary"])),
            }
        )
        corrupted.loc[idx, "summary"] = ""
    log_entries.append(
        {
            "scenario": 2,
            "type": "blank_summary",
            "description": "Xóa rỗng trường summary để kiểm thử Quality Gate (ExpectColumnValueLengthsToBeBetween)",
            "affected_count": len(blank_indices),
            "affected_records": blanked_info,
        }
    )

    # 3. Inject noise (2 bản ghi tiếp theo)
    noise_indices = [2, 3] if len(corrupted) >= 4 else []
    noise_str = " [CORRUPTED_GARBAGE_NOISE: %$#@! NULL REF INVALID_TOKEN_404 UNKNOWN_PAYLOAD ERROR]"
    noise_info = []
    for idx in noise_indices:
        noise_info.append({"paper_id": str(corrupted.loc[idx, "paper_id"])})
        corrupted.loc[idx, "summary"] = str(corrupted.loc[idx, "summary"]) + noise_str
    log_entries.append(
        {
            "scenario": 3,
            "type": "inject_noise",
            "description": "Chèn chuỗi ký tự rác vào summary nhằm làm giảm chất lượng retrieval & answer",
            "affected_count": len(noise_indices),
            "affected_records": noise_info,
        }
    )

    # 4. Truncate title (2 bản ghi tiếp theo, cắt ngắn < 8 ký tự)
    trunc_indices = [4, 5] if len(corrupted) >= 6 else []
    trunc_info = []
    for idx in trunc_indices:
        old_title = str(corrupted.loc[idx, "title"])
        truncated_title = old_title[:6].strip()
        trunc_info.append(
            {
                "paper_id": str(corrupted.loc[idx, "paper_id"]),
                "original_title": old_title,
                "truncated_title": truncated_title,
            }
        )
        corrupted.loc[idx, "title"] = truncated_title
    log_entries.append(
        {
            "scenario": 4,
            "type": "truncate_title",
            "description": "Cắt ngắn tiêu đề bài báo xuống < 8 ký tự làm sai lệch nhận diện tiêu đề của Agent",
            "affected_count": len(trunc_indices),
            "affected_records": trunc_info,
        }
    )

    # 5. Stale date (6 bản ghi tiếp theo, lùi 5 năm để vi phạm Freshness SLA)
    stale_indices = [i for i in range(6, min(12, len(corrupted)))]
    stale_info = []
    for idx in stale_indices:
        old_pub = str(corrupted.loc[idx, "published"])
        parts = old_pub.split("-")
        if len(parts) >= 3:
            new_year = max(1990, int(parts[0]) - 5)
            new_pub = f"{new_year:04d}-{parts[1]}-{parts[2]}"
        else:
            new_pub = "2021-01-01"
        stale_info.append(
            {
                "paper_id": str(corrupted.loc[idx, "paper_id"]),
                "original_published": old_pub,
                "corrupted_published": new_pub,
            }
        )
        corrupted.loc[idx, "published"] = new_pub
        corrupted.loc[idx, "updated"] = new_pub
    log_entries.append(
        {
            "scenario": 5,
            "type": "stale_date",
            "description": "Lùi ngày xuất bản về quá khứ 5 năm làm tỷ lệ stale > 25% vi phạm Freshness SLA",
            "affected_count": len(stale_indices),
            "affected_records": stale_info,
        }
    )

    # 6. Duplicate rows (nhân bản 2 dòng có sẵn để vi phạm ExpectColumnValuesToBeUnique)
    dup_indices = [12, 13] if len(corrupted) >= 14 else [0]
    dups = corrupted.iloc[dup_indices].copy()
    dup_info = [str(pid) for pid in dups["paper_id"]]
    corrupted = pd.concat([corrupted, dups], ignore_index=True)
    log_entries.append(
        {
            "scenario": 6,
            "type": "duplicate_rows",
            "description": "Nhân bản bản ghi để tạo ID trùng lặp, vi phạm ExpectColumnValuesToBeUnique",
            "affected_count": len(dups),
            "duplicated_paper_ids": dup_info,
        }
    )

    # Rebuild helper columns
    run_date_naive = datetime.now(UTC).replace(tzinfo=None)

    def _calc_age(pub_str: Any) -> int:
        try:
            pub_dt = datetime.strptime(str(pub_str)[:10], "%Y-%m-%d")
            return max(0, (run_date_naive - pub_dt).days)
        except Exception:
            return 0

    corrupted["summary_chars"] = corrupted["summary"].apply(lambda s: len(str(s or "")))
    corrupted["age_days"] = corrupted["published"].apply(_calc_age)
    corrupted["text_for_embedding"] = corrupted.apply(
        lambda row: format_text_for_embedding(
            title=str(row["title"]),
            authors_joined=str(row["authors_joined"]),
            published=str(row["published"]),
            categories_joined=str(row["categories_joined"]),
            summary=str(row["summary"]),
        ),
        axis=1,
    )

    # Ghi corruption log
    log_path = Path(output_log_path) if output_log_path else Path("data/results/corruption_log.json")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "original_row_count": original_count,
        "corrupted_row_count": len(corrupted),
        "total_scenarios": 6,
        "scenarios": log_entries,
    }
    log_path.write_text(json.dumps(log_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return corrupted


def save_corrupted_artifacts(df: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    """Lưu corrupted dataframe ra file CSV và JSON."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records", indent=2, force_ascii=False)
