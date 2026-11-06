"""Split conformal prediction engine for distribution-free uncertainty quantification."""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor

from app.schemas.uncertainty import SubgroupCoverageMetric
from app.ml.preprocessing import ALL_FEATURE_NAMES, TARGET_VARIABLE


def compute_nonconformity_scores(
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> np.ndarray:
    """Compute absolute residual nonconformity scores: s_i = |y_i - y_hat_i|."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return np.abs(y_true - y_pred)


def calculate_conformal_quantile(
    scores: np.ndarray,
    nominal_coverage: float,
) -> Tuple[float, float, bool]:
    """Calculate finite-sample adjusted conformal quantile for nominal coverage 1 - alpha.

    In split conformal prediction, the critical value is the k-th order statistic:
    k = ceil((n + 1) * (1 - alpha))
    Guarantees: P(Y in C(X)) >= 1 - alpha under exchangeability.

    Returns:
        (quantile_value, adjusted_percentile, is_theoretically_guaranteed)
    """
    n = len(scores)
    if n == 0:
        return 0.0, 0.0, False

    alpha = 1.0 - nominal_coverage
    k = int(np.ceil((n + 1) * (1.0 - alpha)))
    p = k / n

    sorted_scores = np.sort(scores)

    if k > n:
        # Sample size n is too small to guarantee nominal coverage (n < 1/alpha - 1)
        # e.g., for 95% coverage, n must be >= 19.
        return float(sorted_scores[-1]), 1.0, False

    # 0-indexed k-th order statistic
    q_val = float(sorted_scores[k - 1])
    return q_val, round(p, 4), True


def generate_prediction_interval(
    point_estimate: float,
    quantile_q: float,
) -> Tuple[float, float, float, float]:
    """Construct lower bound, upper bound, interval width, and relative percentage width."""
    y_hat = max(0.0, float(point_estimate))
    lower = max(0.0, round(y_hat - quantile_q, 2))
    upper = round(y_hat + quantile_q, 2)
    width = round(upper - lower, 2)
    rel_width_pct = round((width / max(1.0, y_hat)) * 100.0, 2)

    return lower, upper, width, rel_width_pct


def evaluate_subgroup_coverage(
    cal_df: pd.DataFrame,
    scores: np.ndarray,
    quantiles_by_coverage: Dict[float, float],
) -> List[SubgroupCoverageMetric]:
    """Inspect empirical coverage across cities, localities, property types, and size categories."""
    metrics: List[SubgroupCoverageMetric] = []
    df = cal_df.copy()
    df["nonconformity_score"] = scores

    # 1. Area Tier categorization
    def categorize_area(area: float) -> str:
        if area < 900:
            return "Compact (< 900 sq ft)"
        elif area <= 1600:
            return "Mid-Size (900 - 1600 sq ft)"
        return "Large (> 1600 sq ft)"

    df["area_tier"] = df["carpet_area_sqft"].apply(categorize_area)

    subgroup_columns = ["city", "locality", "property_type", "area_tier", "transaction_quarter"]

    for col in subgroup_columns:
        if col not in df.columns:
            continue

        for val, group in df.groupby(col):
            subgroup_size = len(group)
            if subgroup_size < 3:
                continue

            for cov_level, q_val in quantiles_by_coverage.items():
                covered_count = int(np.sum(group["nonconformity_score"] <= q_val))
                emp_cov = round(covered_count / subgroup_size, 4)
                interval_width = round(2.0 * q_val, 2)
                # Flag if empirical coverage is significantly below nominal (> 5% deficit)
                is_under = emp_cov < (cov_level - 0.05)

                metrics.append(
                    SubgroupCoverageMetric(
                        subgroupCategory=col,
                        subgroupValue=str(val),
                        sampleSize=subgroup_size,
                        nominalCoverage=cov_level,
                        empiricalCoverage=emp_cov,
                        meanIntervalWidth=interval_width,
                        isUnderCovered=is_under,
                    )
                )

    return metrics


def calibrate_conformal_model(
    model: CatBoostRegressor,
    cal_df: pd.DataFrame,
    coverage_levels: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """Execute split conformal calibration on an isolated holdout dataset."""
    if coverage_levels is None:
        coverage_levels = [0.90, 0.95]

    X_cal = cal_df[ALL_FEATURE_NAMES].copy()
    y_cal = cal_df[TARGET_VARIABLE].values

    y_pred = model.predict(X_cal)
    scores = compute_nonconformity_scores(y_cal, y_pred)

    quantiles: Dict[str, float] = {}
    mean_widths: Dict[str, float] = {}
    quantiles_numeric: Dict[float, float] = {}

    for cov in coverage_levels:
        q_val, _, _ = calculate_conformal_quantile(scores, cov)
        quantiles[str(cov)] = round(q_val, 2)
        mean_widths[str(cov)] = round(2.0 * q_val, 2)
        quantiles_numeric[cov] = q_val

    subgroup_metrics = evaluate_subgroup_coverage(cal_df, scores, quantiles_numeric)

    return {
        "sample_size": len(cal_df),
        "coverage_levels": coverage_levels,
        "quantiles": quantiles,
        "mean_interval_width": mean_widths,
        "subgroup_metrics": [m.model_dump(by_alias=True) for m in subgroup_metrics],
        "scores_distribution": {
            "min": round(float(np.min(scores)), 2),
            "median": round(float(np.median(scores)), 2),
            "mean": round(float(np.mean(scores)), 2),
            "max": round(float(np.max(scores)), 2),
        },
    }
