# Corruption and Recovery Report

## Baseline vs Corrupted vs Repaired

| Metric | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| retrieval_hit_rate | 1.0000 | 1.0000 | 1.0000 |
| mean_token_f1 | 0.7076 | 0.5611 | 0.7076 |
| judge_accuracy | 0.5000 | 0.6000 | 0.8000 |
| mean_judge_score | 3.4000 | 3.2000 | 3.6000 |

## Data Quality

- Corrupted quality gate: FAIL
- Repaired quality gate: PASS

## Freshness

- Corrupted freshness: STALE / UNVERIFIED
- Repaired freshness: FRESH

## Degradation and Recovery

- Mean token F1 change after corruption: -0.1465.
- Mean token F1 recovery after repair: +0.1465.
