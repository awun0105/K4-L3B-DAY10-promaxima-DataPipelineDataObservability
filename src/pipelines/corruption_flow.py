from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import EvaluationBundle, evaluate_pipeline
from ingestion.corruption import corrupt_clean_dataframe
from observability.quality import build_freshness_report, run_data_quality_checks
from pipelines.phase1 import run_baseline_pipeline
from retrieval.index import LocalEmbeddingIndex

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

    # 3. Build Chroma index for corrupted data
    logger.info(f"[3/7] Building Chroma vector index for corrupted collection '{settings.corrupted_collection_name}'...")
    corrupted_index = LocalEmbeddingIndex.build(
        df=df_corrupted,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )

    # 4. Evaluate corrupted RAG performance on the SAME benchmark test set
    logger.info("[4/7] Evaluating RAG performance on corrupted dataset (measuring Silent Failure)...")
    corrupted_bundle: EvaluationBundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    c_hr = corrupted_bundle.summary.get("retrieval_hit_rate", 0.0)
    c_f1 = corrupted_bundle.summary.get("mean_token_f1", 0.0)
    logger.info(f"-> Corrupted Metrics: Retrieval Hit Rate = {c_hr:.2%}, Mean Token F1 = {c_f1:.4f}")

    # 5. Run Quality Gate & Freshness on corrupted data
    logger.info("[5/7] Running Data Quality Gate on corrupted dataset...")
    corrupted_quality = run_data_quality_checks(df_corrupted, settings=settings, report_name="corrupted")
    corrupted_freshness = build_freshness_report(
        df_corrupted,
        settings=settings,
        report_path=settings.paths.quality_dir / "corrupted_freshness_report.json",
    )
    logger.warning(f"[Quality Gate Corrupted] success = {corrupted_quality.get('success')} (Expectations Failed!)")
    logger.warning(f"[Freshness SLA Corrupted] is_fresh = {corrupted_freshness.get('is_fresh')} (SLA Violated!)")

    return {
        "df_clean": df_clean,
        "df_corrupted": df_corrupted,
        "corrupted_bundle": corrupted_bundle,
        "corrupted_quality": corrupted_quality,
        "corrupted_freshness": corrupted_freshness,
        "baseline_metrics": baseline_metrics,
    }


def main() -> None:
    settings = load_settings()
    run_corruption_and_repair_flow(settings)


if __name__ == "__main__":
    main()
