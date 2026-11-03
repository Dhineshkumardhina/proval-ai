"""SHAP-based model explainability engine with strict distinction from rule-based hedonic math."""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor, Pool
import shap

from app.schemas.ml import SHAPFeatureContribution
from app.ml.preprocessing import FEATURE_NAMES_CATEGORICAL, ALL_FEATURE_NAMES


def explain_catboost_prediction(
    model: CatBoostRegressor,
    feature_row: pd.DataFrame,
) -> Tuple[float, List[SHAPFeatureContribution]]:
    """Compute local SHAP (TreeSHAP) feature attributions for a single valuation input.

    Uses CatBoost's native TreeSHAP implementation to derive exact feature contributions:
    Price = Base_Value + sum(SHAP_i)
    """
    # Ensure correct columns and order
    row_df = feature_row[ALL_FEATURE_NAMES].copy()

    pool = Pool(data=row_df, cat_features=FEATURE_NAMES_CATEGORICAL)
    shap_matrix = model.get_feature_importance(data=pool, type="ShapValues")

    # In CatBoost ShapValues, the last element is the expected base value E[f(x)]
    base_value = float(shap_matrix[0, -1])
    feature_shaps = shap_matrix[0, :-1]

    contributions: List[SHAPFeatureContribution] = []

    for idx, col_name in enumerate(ALL_FEATURE_NAMES):
        shap_val = float(feature_shaps[idx])
        val = row_df[col_name].iloc[0]

        if shap_val > 1000.0:
            direction = "INCREASES_VALUE"
            desc = f"{col_name} ({val}) increases estimated valuation by ₹{abs(shap_val):,.0f}"
        elif shap_val < -1000.0:
            direction = "DECREASES_VALUE"
            desc = f"{col_name} ({val}) reduces estimated valuation by ₹{abs(shap_val):,.0f}"
        else:
            direction = "NEUTRAL"
            desc = f"{col_name} ({val}) has negligible marginal impact (₹{shap_val:,.0f})"

        contributions.append(
            SHAPFeatureContribution(
                feature=col_name,
                featureValue=val,
                shapValue=round(shap_val, 2),
                impactDirection=direction,
                impactDescription=desc,
            )
        )

    # Sort descending by absolute impact
    contributions.sort(key=lambda c: abs(c.shapValue), reverse=True)

    return round(base_value, 2), contributions


def get_governance_provenance_notice(is_ml: bool, model_version: Optional[str] = None) -> Dict[str, str]:
    """Return explicit governance taxonomy distinguishing SHAP ML attributions from rule-based factors."""
    if is_ml:
        return {
            "methodology": "TreeSHAP (SHapley Additive exPlanations)",
            "source": f"CatBoost Gradient Boosted Ensemble ({model_version or 'v1.0'})",
            "mathematical_basis": "Marginal coalition game-theoretic attribution computed across decision trees",
            "statutory_status": "Statistical approximation based on verified empirical deed registrations",
            "rule_based_overlap": "Independent of statutory circle rate tables and underwriter heuristic haircuts",
        }
    else:
        return {
            "methodology": "Statutory Rule-Based Hedonic Arithmetic",
            "source": "State Guidance Value / Circle Rate Gazette & Fixed Heuristic Factors",
            "mathematical_basis": "Area × Guidance Rate × (1 + Floor Rise) × (1 - Age Depreciation)",
            "statutory_status": "Deterministic baseline estimation under Phase 1/2 credibility guidelines",
            "rule_based_overlap": "This is NOT an ML prediction and contains NO SHAP explanations",
        }

