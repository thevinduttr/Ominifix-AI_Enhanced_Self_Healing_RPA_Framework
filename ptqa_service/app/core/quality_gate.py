from typing import Any, Dict, List


def evaluate_quality(
    healing_id: str,
    prediction: Dict[str, Any],
    metrics: Dict[str, Any],
    validation_steps: List[str],
) -> Dict[str, Any]:
    p_fail = float(prediction.get("p_fail", 0.5))
    risk_level = prediction.get("risk_level", "MEDIUM")
    will_work_prob = float(prediction.get("will_work_probability", 0.5))

    reliability_score = float(metrics.get("reliability_score", 50.0))
    healing_accuracy = float(metrics.get("healing_accuracy", 0.0))
    recovery_latency = float(metrics.get("recovery_latency", 0.0))
    has_regression = bool(metrics.get("has_regression", False))
    regression_impact = metrics.get("regression_impact", "UNKNOWN")

    recommendation = "APPROVE_HEALING"
    reasons: List[str] = []

    if p_fail >= 0.7 or reliability_score < 50:
        recommendation = "BLOCK_HEALING"
        reasons.append("High predicted failure risk or low reliability score.")
    elif p_fail >= 0.5 or reliability_score < 70:
        recommendation = "WARN"
        reasons.append("Moderate predicted risk or borderline reliability.")

    if healing_accuracy < 0.8:
        reasons.append("Healing accuracy below 80%.")

    if has_regression:
        reasons.append(f"Performance regression detected ({regression_impact}).")

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
