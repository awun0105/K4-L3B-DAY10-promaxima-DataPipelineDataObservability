from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import re
from typing import Any, Sequence

import pandas as pd

from ingestion.crossref import PaperRecord


def clean_text(value: str | None) -> str:
    """Loại bỏ thẻ XML/HTML thừa và chuẩn hóa khoảng trắng."""
    if not value:
        return ""
    stripped = re.sub(r"<[^>]+>", "", str(value))
    return re.sub(r"\s+", " ", stripped).strip()


def format_text_for_embedding(
    title: str,
    authors_joined: str,
    published: str,
    categories_joined: str,
    summary: str,
) -> str:
    """Ghép chuỗi embedding chuẩn hóa gồm 5 phần theo Rubric & Contract."""
    return (
        f"Title: {title}\n"
        f"Authors: {authors_joined}\n"
        f"Published: {published}\n"
        f"Categories: {categories_joined}\n"
        f"Summary: {summary}"
    )


def _extract_field(record: PaperRecord | dict[str, Any], key: str, default: Any = "") -> Any:
    """Trích xuất trường dữ liệu an toàn từ PaperRecord hoặc dict."""
    if isinstance(record, dict):
        return record.get(key, default)
    return getattr(record, key, default)


def build_clean_dataframe(records: Sequence[PaperRecord | dict[str, Any]], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thành DataFrame chuẩn hóa sẵn sàng để embed và observability.

    Quy trình xử lý:
    1. Khử trùng lặp bản ghi theo `paper_id` (giữ bản ghi đầu tiên).
    2. Chuẩn hóa text cho `title`, `summary`, `authors`, `categories` (loại bỏ JATS XML & khoảng trắng).
    3. Loại bỏ bản ghi không hợp lệ (thiếu `paper_id`, thiếu `title`, hoặc `summary` < 10 ký tự).
    4. Parse ngày xuất bản `published` và tính `age_days = (run_date - published).days`.
    5. Tạo các cột phụ trợ:
       - `authors_joined`: Chuỗi tác giả nối nhau bởi dấu phẩy.
       - `categories_joined`: Chuỗi chuyên mục nối nhau bởi dấu phẩy.
       - `summary_chars`: Độ dài số ký tự của summary.
       - `text_for_embedding`: Chuỗi 5 phần (Title, Authors, Published, Categories, Summary).
    6. Sắp xếp DataFrame theo `paper_id` và reset index.
    """
    if run_date.tzinfo is not None:
        run_date_naive = run_date.astimezone(UTC).replace(tzinfo=None)
    else:
        run_date_naive = run_date

    seen_ids: set[str] = set()
    cleaned_rows: list[dict[str, Any]] = []

    for item in records:
        raw_id = _extract_field(item, "paper_id", "")
        paper_id = clean_text(raw_id)
        if not paper_id or paper_id in seen_ids:
            continue
        seen_ids.add(paper_id)

        title = clean_text(_extract_field(item, "title", ""))
        summary = clean_text(_extract_field(item, "summary", ""))
        if not title or len(summary) < 10:
            continue

        raw_authors = _extract_field(item, "authors", []) or []
        authors = [clean_text(a) for a in raw_authors if clean_text(a)]

        raw_categories = _extract_field(item, "categories", []) or []
        categories = [clean_text(c) for c in raw_categories if clean_text(c)]

        primary_cat = _extract_field(item, "primary_category", "")
        primary_category = clean_text(primary_cat) if primary_cat else (categories[0] if categories else "")

        pub_str = clean_text(_extract_field(item, "published", ""))
        try:
            pub_dt = datetime.strptime(pub_str[:10], "%Y-%m-%d")
            age_days = max(0, (run_date_naive - pub_dt).days)
        except Exception:
            pub_dt = run_date_naive
            age_days = 0

        published = pub_str[:10] if pub_str else run_date_naive.strftime("%Y-%m-%d")
        updated_str = clean_text(_extract_field(item, "updated", ""))
        updated = updated_str[:10] if updated_str else published

        abs_url = clean_text(_extract_field(item, "abs_url", ""))
        pdf_url = clean_text(_extract_field(item, "pdf_url", ""))
        comment = clean_text(_extract_field(item, "comment", f"Crossref record {paper_id}"))

        authors_joined = ", ".join(authors)
        categories_joined = ", ".join(categories)
        summary_chars = len(summary)

        text_for_embedding = format_text_for_embedding(
            title=title,
            authors_joined=authors_joined,
            published=published,
            categories_joined=categories_joined,
            summary=summary,
        )

        cleaned_rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": primary_category,
                "published": published,
                "updated": updated,
                "abs_url": abs_url,
                "pdf_url": pdf_url,
                "comment": comment,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": summary_chars,
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(cleaned_rows)
    if not df.empty:
        df = df.sort_values(by="paper_id").reset_index(drop=True)
    return df


def save_clean_dataframe(df: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    """Lưu Cleaned DataFrame ra cả 2 định dạng artifact CSV và JSON."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records", indent=2, force_ascii=False)
