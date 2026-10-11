"""Deterministic, explainable city scoring. No LLM is used for calculations."""
from __future__ import annotations
import pandas as pd

DEFAULT_WEIGHTS = {
    "talent_depth": 35,
    "operating_cost": 25,
    "ecosystem": 25,
    "infrastructure": 15,
}
METRICS = list(DEFAULT_WEIGHTS)

def score_cities(metrics: pd.DataFrame, weights: dict[str, float]) -> pd.DataFrame:
    """Score cities from metric values already expressed on a 0-100 desirability scale.

    `operating_cost` is an attractiveness score (higher means more attractive),
    not raw currency expenditure. Missing metrics are excluded from a city's
    weighted average and lower its evidence coverage.
    """
    if metrics.empty:
        return pd.DataFrame(columns=["city", "overall_score", "evidence_coverage", *METRICS])
    normalized_weights = {k: max(0.0, float(weights.get(k, 0))) for k in METRICS}
    total_weight = sum(normalized_weights.values())
    if total_weight <= 0:
        raise ValueError("At least one metric weight must be greater than zero.")

    wide = metrics.pivot_table(index="city", columns="metric_key", values="value", aggfunc="mean")
    for metric in METRICS:
        if metric not in wide.columns:
            wide[metric] = float("nan")
    wide = wide[METRICS].apply(pd.to_numeric, errors="coerce")
    scores, coverage = [], []
    active = {k: v / total_weight for k, v in normalized_weights.items() if v > 0}
    for _, row in wide.iterrows():
        available = {k: w for k, w in active.items() if pd.notna(row[k])}
        available_weight = sum(available.values())
        if available_weight == 0:
            scores.append(float("nan"))
        else:
            scores.append(sum(float(row[k]) * w for k, w in available.items()) / available_weight)
        coverage.append(100 * sum(1 for k in METRICS if pd.notna(row[k])) / len(METRICS))
    wide["overall_score"] = scores
    wide["evidence_coverage"] = coverage
    wide = wide.reset_index()
    return wide
