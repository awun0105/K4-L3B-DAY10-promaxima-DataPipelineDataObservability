from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
import time
from typing import Any

import requests

from core.config import Settings
from core.utils import read_json, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict[str, Any]) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord.

    1. Duyet `payload["message"]["items"]` (hoac `payload["items"]`).
    2. Lay DOI, title, abstract (loai bo tag JATS XML/HTML), authors, subject, dates, URLs.
    3. Chuan hoa text va loai bo record khong hop le (thieu DOI hoac title).
    4. Tra ve list `PaperRecord`.
    """
    items = payload.get("message", {}).get("items")
    if items is None:
        items = payload.get("items", [])

    records: list[PaperRecord] = []
    for item in items:
        doi = item.get("DOI", "").strip()
        if not doi:
            continue

        title_list = item.get("title", [])
        if isinstance(title_list, list) and title_list:
            title = str(title_list[0]).strip()
        elif isinstance(title_list, str):
            title = title_list.strip()
        else:
            title = ""
        title = re.sub(r"\s+", " ", title).strip()
        if not title:
            continue

        abstract = item.get("abstract", "") or ""
        # Remove JATS XML / HTML tags like <jats:p>, </jats:p>, <jats:title>, etc.
        summary = re.sub(r"<[^>]+>", "", abstract)
        summary = re.sub(r"\s+", " ", summary).strip()

        authors: list[str] = []
        for author in item.get("author", []):
            given = author.get("given", "").strip()
            family = author.get("family", "").strip()
            if given or family:
                full_name = f"{given} {family}".strip()
            else:
                full_name = author.get("name", "").strip()
            if full_name:
                authors.append(re.sub(r"\s+", " ", full_name))

        categories = [re.sub(r"\s+", " ", str(cat)).strip() for cat in item.get("subject", []) if cat]
        primary_category = categories[0] if categories else ""

        # Extract published date from date-parts: [[YYYY, MM, DD]]
        date_parts = item.get("published", {}).get("date-parts", [[]])[0]
        if len(date_parts) >= 3:
            published = f"{date_parts[0]:04d}-{date_parts[1]:02d}-{date_parts[2]:02d}"
        elif len(date_parts) == 2:
            published = f"{date_parts[0]:04d}-{date_parts[1]:02d}-01"
        elif len(date_parts) == 1:
            published = f"{date_parts[0]:04d}-01-01"
        else:
            dt = item.get("created", {}).get("date-time", "")
            published = dt[:10] if dt and len(dt) >= 10 else ""

        updated = published

        url = item.get("URL", f"https://doi.org/{doi}").strip()
        abs_url = url
        pdf_url = url
        comment = f"Crossref record {doi}"

        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=comment,
            )
        )
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi source API, luu raw response, parse thanh records.

    1. Tao params tu `settings.source_query`, `settings.source_filter`, `settings.max_results`.
    2. Goi API voi retry cho cac status code nhu 429/503 neu settings.refresh_source bat.
    3. Tu dong fallback doc snapshot `data/raw/crossref_response.json` neu offline/loi API/refresh_source tat.
    4. Luu raw response vao `settings.paths.raw_api_response`.
    5. Parse payload bang `parse_crossref_payload`.
    6. Luu records vao `settings.paths.raw_records_json`.
    7. Tra ve list `PaperRecord`.
    """
    payload: dict[str, Any] | None = None

    if settings.refresh_source:
        url = "https://api.crossref.org/works"
        params: dict[str, Any] = {
            "query": settings.source_query,
            "rows": settings.max_results,
        }
        if settings.source_filter:
            params["filter"] = settings.source_filter

        headers = {
            "User-Agent": "Day10ObservabilityLab/1.0 (mailto:diendls321@gmail.com; mailto:quanlam0105@gmail.com)"
        }

        max_retries = 3
        backoff = 1.0
        for _ in range(max_retries):
            try:
                response = requests.get(url, params=params, headers=headers, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("message", {}).get("items"):
                        payload = data
                        write_json(settings.paths.raw_api_response, payload)
                        break
                elif response.status_code in {429, 503}:
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    break
            except Exception:
                time.sleep(backoff)
                backoff *= 2

    # Fallback ve snapshot local neu API khong duoc bat hoac khong thanh cong
    if payload is None:
        if settings.paths.raw_api_response.exists():
            payload = read_json(settings.paths.raw_api_response)
        elif settings.paths.raw_records_json.exists():
            return load_raw_records(settings.paths.raw_records_json)
        else:
            raise FileNotFoundError(
                f"Cannot fetch live Crossref API and local snapshots do not exist: "
                f"{settings.paths.raw_api_response} / {settings.paths.raw_records_json}"
            )

    records = parse_crossref_payload(payload)

    # Neu snapshot parsing cho ket qua, luu lai artifacts raw_records_json
    if records:
        write_json(settings.paths.raw_records_json, [asdict(r) for r in records])

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh `PaperRecord`."""
    data = read_json(path)
    records: list[PaperRecord] = []
    for item in data:
        records.append(
            PaperRecord(
                paper_id=item["paper_id"],
                title=item["title"],
                summary=item.get("summary", ""),
                authors=list(item.get("authors", [])),
                categories=list(item.get("categories", [])),
                primary_category=item.get("primary_category", ""),
                published=item.get("published", ""),
                updated=item.get("updated", ""),
                abs_url=item.get("abs_url", ""),
                pdf_url=item.get("pdf_url", ""),
                comment=item.get("comment", ""),
            )
        )
    return records
