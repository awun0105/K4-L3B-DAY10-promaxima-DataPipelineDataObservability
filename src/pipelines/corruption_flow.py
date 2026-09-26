from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import EvaluationBundle, evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from pipelines.phase1 import run_baseline_pipeline
from retrieval.index import LocalEmbeddingIndex

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("corruption_flow")


def print_comparison_table(
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Print an eye-catching 3-state comparison table in the console for Live Demo."""
    b_hr = baseline_metrics.get("retrieval_hit_rate", 0.0)
    c_hr = corrupted_metrics.get("retrieval_hit_rate", 0.0)
    r_hr = repaired_metrics.get("retrieval_hit_rate", 0.0)

    b_f1 = baseline_metrics.get("mean_token_f1", 0.0)
    c_f1 = corrupted_metrics.get("mean_token_f1", 0.0)
    r_f1 = repaired_metrics.get("mean_token_f1", 0.0)

    b_acc = baseline_metrics.get("judge_accuracy", 0.0)
    c_acc = corrupted_metrics.get("judge_accuracy", 0.0)
    r_acc = repaired_metrics.get("judge_accuracy", 0.0)

    b_score = baseline_metrics.get("mean_judge_score", 0.0)
    c_score = corrupted_metrics.get("mean_judge_score", 0.0)
    r_score = repaired_metrics.get("mean_judge_score", 0.0)

    c_gx = "PASS" if corrupted_quality.get("success") else "FAIL (ALARM)"
    r_gx = "PASS" if repaired_quality.get("success") else "FAIL"

    c_fresh = "FRESH" if corrupted_freshness.get("is_fresh") else "STALE (SLA VIOLATION)"
    r_fresh = "FRESH" if repaired_freshness.get("is_fresh") else "STALE"

    print("\n" + "=" * 80)
    print("      DATA OBSERVABILITY & RAG BENCHMARK: 3-STATE QUANTITATIVE COMPARISON       ")
    print("=" * 80)
    print(f"{'Metric / Signal':<28} | {'Baseline':<14} | {'Corrupted':<16} | {'Repaired':<14}")
    print("-" * 80)
    print(f"{'Retrieval Hit Rate':<28} | {b_hr:<14.2%} | {c_hr:<16.2%} | {r_hr:<14.2%}")
    print(f"{'Mean Token F1':<28} | {b_f1:<14.4f} | {c_f1:<16.4f} | {r_f1:<14.4f}")
    print(f"{'Judge Accuracy':<28} | {b_acc:<14.2%} | {c_acc:<16.2%} | {r_acc:<14.2%}")
    print(f"{'Mean Judge Score (1-5)':<28} | {b_score:<14.2f} | {c_score:<16.2f} | {r_score:<14.2f}")
    print(f"{'GX Quality Gate':<28} | {'PASS':<14} | {c_gx:<16} | {r_gx:<14}")
    print(f"{'Freshness SLA':<28} | {'FRESH':<14} | {c_fresh:<16} | {r_fresh:<14}")
    print("=" * 80 + "\n")


def run_corruption_and_repair_flow(settings: Settings | None = None) -> dict[str, Any]:
    """Execute end-to-end Data Corruption, Silent Failure Evaluation,

    Idempotent Repair, and 3-State Comparison Reporting.

    Includes Bonus B2: Automated Self-Healing / Auto-Repair Pipeline.
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

    # 6. Idempotent Repair & Bonus B2 Auto Self-Healing
    logger.info("--------------------------------------------------------------------------------")
    if not corrupted_quality.get("success") or not corrupted_freshness.get("is_fresh"):
        logger.warning("[BONUS B2: AUTO SELF-HEALING] Data Quality / Freshness Gate triggered ALARM!")
        logger.info("[BONUS B2: AUTO SELF-HEALING] Autonomously initiating Idempotent Repair from raw snapshot...")
    else:
        logger.info("[6/7] Initiating Idempotent Repair from raw snapshot...")

    raw_snapshot_path = settings.paths.raw_records_json
    if not raw_snapshot_path.exists():
        raw_snapshot_path = settings.paths.raw_api_response

    raw_records = load_raw_records(raw_snapshot_path)
    df_repaired = build_clean_dataframe(raw_records, run_date=now_utc())
    write_csv(df_repaired, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, df_repaired.to_dict(orient="records"))
    logger.info(f"-> Idempotent Repair restored clean dataset with {len(df_repaired)} rows.")

    # Re-build index for repaired collection
    repaired_index = LocalEmbeddingIndex.build(
        df=df_repaired,
        settings=settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )

    # Re-evaluate repaired RAG on the SAME test set
    repaired_bundle: EvaluationBundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    r_hr = repaired_bundle.summary.get("retrieval_hit_rate", 0.0)
    r_f1 = repaired_bundle.summary.get("mean_token_f1", 0.0)
    logger.info(f"-> Repaired Metrics: Retrieval Hit Rate = {r_hr:.2%}, Mean Token F1 = {r_f1:.4f}")

    # Re-run quality gate on repaired data
    repaired_quality = run_data_quality_checks(df_repaired, settings=settings, report_name="repaired")
    repaired_freshness = build_freshness_report(
        df_repaired,
        settings=settings,
        report_path=settings.paths.quality_dir / "repaired_freshness_report.json",
    )
    logger.info(f"-> Repaired Quality Gate: success = {repaired_quality.get('success')} (Restored to Green!)")
    logger.info(f"-> Repaired Freshness SLA: is_fresh = {repaired_freshness.get('is_fresh')}")

    # 7. Generate comparison report & display console table
    logger.info(f"[7/7] Generating 3-state comparison Markdown report at {settings.paths.comparison_report}...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_bundle.summary,
        repaired_metrics=repaired_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    # Display console table for Live Demo
    print_comparison_table(
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_bundle.summary,
        repaired_metrics=repaired_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    logger.info("================================================================================")
    logger.info("       CORRUPTION, EVALUATION & REPAIR FLOW COMPLETED SUCCESSFULLY!             ")
    logger.info("================================================================================")

    return {
        "df_corrupted": df_corrupted,
        "df_repaired": df_repaired,
        "corrupted_bundle": corrupted_bundle,
        "repaired_bundle": repaired_bundle,
        "corrupted_quality": corrupted_quality,
        "repaired_quality": repaired_quality,
        "corrupted_freshness": corrupted_freshness,
        "repaired_freshness": repaired_freshness,
    }


def main() -> None:
    settings = load_settings()
    run_corruption_and_repair_flow(settings)


if __name__ == "__main__":
    main()
