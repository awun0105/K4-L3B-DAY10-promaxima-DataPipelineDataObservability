from __future__ import annotations

import logging
from typing import Any

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import EvaluationBundle, evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from retrieval.index import LocalEmbeddingIndex

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

    # 3. Clean raw records
    logger.info("[2/8] Cleaning raw records and constructing `text_for_embedding`...")
    run_date = now_utc()
    df_clean = build_clean_dataframe(records, run_date=run_date)
    logger.info(f"-> Clean DataFrame generated with {len(df_clean)} rows.")

    # 4. Save clean artifacts
    logger.info(f"[3/8] Persisting clean dataset to {settings.paths.clean_csv} & {settings.paths.clean_json}...")
    write_csv(df_clean, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, df_clean.to_dict(orient="records"))

    # 5. Build vector index
    logger.info(f"[4/8] Building Chroma vector index for collection '{settings.baseline_collection_name}'...")
    index = LocalEmbeddingIndex.build(
        df=df_clean,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )
    logger.info(f"-> Indexed {len(index.documents)} documents into collection '{index.collection_name}'.")

    # 6. Build or load test set
    if settings.paths.eval_testset.exists() and not settings.refresh_test_set:
        logger.info(f"[5/8] Loading existing evaluation test set from {settings.paths.eval_testset}...")
        test_set = read_json(settings.paths.eval_testset)
    else:
        logger.info(f"[5/8] Generating 10-question evaluation benchmark test set into {settings.paths.eval_testset}...")
        test_set = build_test_set(df_clean, output_path=settings.paths.eval_testset)
    logger.info(f"-> Evaluation test set contains {len(test_set)} benchmark questions.")

    # 7. Evaluate baseline pipeline
    logger.info("[6/8] Evaluating baseline RAG retrieval and answer quality...")
    eval_bundle: EvaluationBundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    hit_rate = eval_bundle.summary.get("retrieval_hit_rate", 0.0)
    token_f1 = eval_bundle.summary.get("mean_token_f1", 0.0)
    logger.info(f"-> Baseline Metrics: Retrieval Hit Rate = {hit_rate:.2%}, Mean Token F1 = {token_f1:.4f}")

    return {
        "records": records,
        "df_clean": df_clean,
        "index": index,
        "test_set": test_set,
        "eval_bundle": eval_bundle,
    }


def main() -> None:
    settings = load_settings()
    run_baseline_pipeline(settings)


if __name__ == "__main__":
    main()
