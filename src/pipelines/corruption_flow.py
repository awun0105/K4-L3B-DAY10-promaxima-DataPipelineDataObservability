from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import read_json, write_csv, write_json
from ingestion.corruption import corrupt_clean_dataframe
from pipelines.phase1 import run_baseline_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("corruption_flow")


def run_corruption_and_repair_flow(settings: Settings | None = None) -> dict[str, Any]:
    """Execute end-to-end Data Corruption, Silent Failure Evaluation,
    Idempotent Repair, and 3-State Comparison Reporting.
    """
    if settings is None:
        settings = load_settings()

    logger.info("================================================================================")
    logger.info("       STARTING CORRUPTION, EVALUATION & IDEMPOTENT REPAIR FLOW                 ")
    logger.info("================================================================================")

    # 1. Ensure baseline data and metrics exist
    if not settings.paths.clean_csv.exists() or not settings.paths.baseline_metrics.exists():
        logger.info("[1/7] Baseline artifacts missing. Running baseline pipeline first...")
        run_baseline_pipeline(settings)

    df_clean = pd.read_csv(settings.paths.clean_csv)
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    logger.info(f"[1/7] Loaded baseline dataset ({len(df_clean)} rows) and baseline metrics.")

    # 2. Corrupt data with synthetic errors
    logger.info(f"[2/7] Injecting 6 synthetic data corruption scenarios into {settings.paths.corruption_log}...")
    df_corrupted = corrupt_clean_dataframe(df_clean, output_log_path=settings.paths.corruption_log)
    write_csv(df_corrupted, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, df_corrupted.to_dict(orient="records"))
    logger.info(f"-> Corrupted dataset saved with {len(df_corrupted)} rows.")

    return {"df_clean": df_clean, "df_corrupted": df_corrupted, "baseline_metrics": baseline_metrics}


def main() -> None:
    settings = load_settings()
    run_corruption_and_repair_flow(settings)


if __name__ == "__main__":
    main()
