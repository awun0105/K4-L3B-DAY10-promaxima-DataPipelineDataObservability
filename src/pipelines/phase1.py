from __future__ import annotations

import logging
from typing import Any

from core.config import Settings, load_settings
from ingestion.crossref import fetch_source_records, load_raw_records

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("phase1_pipeline")


def run_baseline_pipeline(settings: Settings | None = None) -> dict[str, Any]:
    """Execute end-to-end Phase 1 Baseline Data Pipeline."""
    if settings is None:
        settings = load_settings()

    logger.info("================================================================================")
    logger.info("               STARTING PHASE 1: BASELINE DATA PIPELINE                         ")
    logger.info("================================================================================")

    # 1 & 2. Ingest or load raw records
    if settings.paths.raw_records_json.exists() and not settings.refresh_source:
        logger.info(f"[1/8] Loading existing raw records from {settings.paths.raw_records_json}...")
        records = load_raw_records(settings.paths.raw_records_json)
    else:
        logger.info("[1/8] Fetching raw records from Crossref API (with snapshot fallback)...")
        records = fetch_source_records(settings)
    logger.info(f"-> Ingested {len(records)} raw records successfully.")

    return {"records": records}


def main() -> None:
    settings = load_settings()
    run_baseline_pipeline(settings)


if __name__ == "__main__":
    main()
