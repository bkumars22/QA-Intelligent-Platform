"""
SHAP explainability layer for QAIP's IsolationForest risk scorer.

explain(clf, feature_matrix, file_paths, normalized_scores) → list[dict]

Each dict contains:
  shap_values   — per-feature contribution to risk (positive = increases risk)
  shap_top      — top 3 features sorted by absolute contribution
  shap_sentence — human-readable summary: "Risk driven by: auth code (+0.41)…"

Falls back to a feature-weight approximation when the `shap` package is absent.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger("qaip.risk_explainer")

FEATURE_NAMES = [
    "lines_changed",
    "file_size_kb",
    "import_count",
    "function_count",
    "has_auth_code",
    "has_db_code",
    "test_coverage_delta",
]

FEATURE_LABELS = {
    "lines_changed":        "large diff",
    "file_size_kb":         "large file",
    "import_count":         "many imports",
    "function_count":       "many functions",
    "has_auth_code":        "auth code",
    "has_db_code":          "DB operations",
    "test_coverage_delta":  "coverage delta",
}


def _shap_sentence(shap_dict: dict[str, float]) -> str:
    """Produce a one-line plain-English summary of the top risk drivers."""
    positive = sorted(
        ((k, v) for k, v in shap_dict.items() if v > 0.01),
        key=lambda x: -x[1],
    )[:3]
    negative = sorted(
        ((k, v) for k, v in shap_dict.items() if v < -0.01),
        key=lambda x: x[1],
    )[:2]

    parts: list[str] = []
    if positive:
        drivers = ", ".join(f"{FEATURE_LABELS[k]} (+{v:.2f})" for k, v in positive)
        parts.append(f"Risk driven by: {drivers}")
    if negative:
        reducers = ", ".join(f"{FEATURE_LABELS[k]} ({v:.2f})" for k, v in negative)
        parts.append(f"reduced by: {reducers}")

    return ". ".join(parts) if parts else "No dominant risk features detected."


def _fallback_explain(
    feature_matrix: np.ndarray,
    normalized_scores: np.ndarray,
) -> list[dict[str, Any]]:
    """
    Approximation when SHAP is unavailable.
    Weights each feature by its z-score * file_risk_score.
    """
    col_mean = feature_matrix.mean(axis=0)
    col_std  = feature_matrix.std(axis=0) + 1e-9
    z_scores = (feature_matrix - col_mean) / col_std   # (n, 7)

    results: list[dict[str, Any]] = []
    for i in range(len(feature_matrix)):
        risk = float(normalized_scores[i])
        # Scale z-scores by risk so high-risk files get bigger values
        approx = {FEATURE_NAMES[j]: round(float(z_scores[i, j]) * risk * 0.3, 4)
                  for j in range(len(FEATURE_NAMES))}

        top3 = sorted(approx.items(), key=lambda x: -abs(x[1]))[:3]
        results.append({
            "shap_values":   approx,
            "shap_top":      [{"feature": k, "label": FEATURE_LABELS[k], "value": v} for k, v in top3],
            "shap_sentence": _shap_sentence(approx),
            "shap_method":   "approximation",
        })
    return results


def explain(
    clf,
    feature_matrix: np.ndarray,
    normalized_scores: np.ndarray,
) -> list[dict[str, Any]]:
    """
    Run SHAP TreeExplainer on a fitted IsolationForest.

    SHAP values for IsolationForest represent contribution to the anomaly
    decision function (higher = more anomalous = higher risk).
    We negate decision_function's sign so positive SHAP = increases risk.
    """
    n = len(feature_matrix)

    try:
        import shap  # type: ignore

        explainer   = shap.TreeExplainer(clf)
        raw_shap    = explainer.shap_values(feature_matrix)   # (n, 7)

        # IsolationForest decision_function: high = normal → low risk
        # Negate so positive SHAP → higher risk contribution
        risk_shap = -np.array(raw_shap, dtype=float)

        results: list[dict[str, Any]] = []
        for i in range(n):
            vals = {FEATURE_NAMES[j]: round(float(risk_shap[i, j]), 4)
                    for j in range(len(FEATURE_NAMES))}
            top3 = sorted(vals.items(), key=lambda x: -abs(x[1]))[:3]
            results.append({
                "shap_values":   vals,
                "shap_top":      [{"feature": k, "label": FEATURE_LABELS[k], "value": v}
                                  for k, v in top3],
                "shap_sentence": _shap_sentence(vals),
                "shap_method":   "shap_tree_explainer",
            })
        logger.info("SHAP TreeExplainer ran on %d files", n)
        return results

    except ImportError:
        logger.info("shap not installed — using feature-weight approximation")
        return _fallback_explain(feature_matrix, normalized_scores)

    except Exception as exc:
        logger.warning("SHAP explanation failed (%s) — falling back to approximation", exc)
        return _fallback_explain(feature_matrix, normalized_scores)
