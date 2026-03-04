# app/core/quality_gate.py

from __future__ import annotations

from typing import Any, Dict, List


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default


def evaluate_quality(
    healing_id: str,
    prediction: Dict[str, Any],
    metrics: Dict[str, Any],
    validation_steps: List[str],
) -> Dict[str, Any]:
    """
    Produces a consistent decision.

    Fixes applied:
    - Risk level can be escalated based on regression_impact (MAJOR => HIGH)
    - Reasons are context-aware: avoids misleading "healing accuracy below 80%" when
      both before and after are failing.
    - BLOCK/WARN logic prioritises MAJOR regression and severe instability.
    """

    p_fail = _safe_float(prediction.get("p_fail", 0.5), 0.5)
    model_risk_level = (prediction.get("risk_level") or "MEDIUM").upper()
    will_work_prob = _safe_float(prediction.get("will_work_probability", 0.5), 0.5)

    reliability_score = _safe_float(metrics.get("reliability_score", 50.0), 50.0)

    # before/after comparators
    pr_before = _safe_float(metrics.get("pass_rate_before", 0.0), 0.0)
    pr_after = _safe_float(metrics.get("pass_rate_after", 0.0), 0.0)
    pr_delta = _safe_float(metrics.get("pass_rate_delta", 0.0), 0.0)

    t_before = _safe_float(metrics.get("avg_time_before", 0.0), 0.0)
    t_after = _safe_float(metrics.get("avg_time_after", 0.0), 0.0)
    lat_delta = _safe_float(metrics.get("latency_delta", 0.0), 0.0)

    healing_effect = (metrics.get("healing_effect") or "NO_CHANGE").upper()

    has_regression = bool(metrics.get("has_regression", False))
    regression_impact = (metrics.get("regression_impact") or "NONE").upper()

    # Start from model risk, then adjust for regression and observed outcomes
    risk_level = model_risk_level

    # Escalate based on observed regression severity
    if regression_impact == "MAJOR":
        risk_level = "HIGH"
    elif regression_impact == "MINOR" and risk_level == "LOW":
        risk_level = "MEDIUM"

    # Decision defaults
    recommendation = "APPROVE_HEALING"
    reasons: List[str] = []

    # 1) Hard gates from observed regression and stability
    # If healed script cannot pass any tests, block (pr_after == 0)
    if pr_after <= 0.0:
        recommendation = "BLOCK_HEALING"
        reasons.append("Healed script did not pass any regression tests (after pass rate = 0%).")

    # MAJOR regression is a hard block
    if regression_impact == "MAJOR":
        recommendation = "BLOCK_HEALING"
        reasons.append("Major regression detected in before vs after comparison.")

    # 2) ML + reliability checks
    if recommendation != "BLOCK_HEALING":
        if p_fail >= 0.7 or reliability_score < 50:
            recommendation = "BLOCK_HEALING"
            reasons.append("High predicted failure probability or low reliability score.")
        elif p_fail >= 0.5 or reliability_score < 70:
            recommendation = "WARN"
            reasons.append("Moderate predicted risk or borderline reliability score.")

    # 3) Context-aware healing improvement reason (fix misleading 'accuracy below 80%')
    # Only mention accuracy threshold if baseline was stable enough or healing effect degraded.
    if pr_before > 0.0 or healing_effect == "DEGRADED":
        if pr_after < 0.8:
            if recommendation == "APPROVE_HEALING":
                recommendation = "WARN"
            reasons.append("After-healing pass rate is below 80% threshold.")

    # 4) Explain effect clearly
    if pr_before == 0.0 and pr_after == 0.0:
        reasons.append("Baseline and healed runs both failed (no stability improvement observed).")
    elif pr_before == 0.0 and pr_after > 0.0:
        reasons.append("Healing improved stability from 0% baseline pass rate to a non-zero pass rate.")
    elif pr_before > 0.0 and pr_after == 0.0:
        reasons.append("Healing reduced stability (baseline passed but healed failed).")
    else:
        reasons.append(f"Healing effect: {healing_effect}.")

    # 5) Regression detail reason
    if has_regression and regression_impact != "MAJOR":
        reasons.append(f"Regression detected ({regression_impact}).")

    # 6) Always include deltas for transparency
    reasons.append(f"Pass-rate (before → after): {pr_before:.3f} → {pr_after:.3f} (Δ {pr_delta:+.3f})")
    reasons.append(f"Avg time (before → after): {t_before:.3f}s → {t_after:.3f}s (Δ {lat_delta:+.3f}s)")

    # If nothing added (should not happen), keep safe default message
    if not reasons:
        reasons.append("Prediction and metrics within acceptable thresholds.")

    return {
        "healing_id": healing_id,
        "will_work_probability": will_work_prob,
        "risk_level": risk_level,
        "recommendation": recommendation,
        "confidence": 1.0 - p_fail,
        "quality_metrics": metrics,
        "validation_steps": validation_steps,
        "reasons": reasons,
        "model_name": prediction.get("model_name"),
    }