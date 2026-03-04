# app/core/metrics_engine.py
"""
metrics_engine.py

Computes quality metrics using BEFORE vs AFTER comparisons.

Key goals:
- Stable before/after pass-rate + time metrics
- Correct regression detection
- Provide "healing_effect" context so quality_gate can write correct reasons
- Avoid misleading "healing_accuracy below 80%" when both before and after failed
"""

from __future__ import annotations

from typing import Any, Dict


def _safe_rate(passed: int, total: int) -> float:
    total = int(total) if total else 0
    passed = int(passed) if passed else 0
    if total <= 0:
        return 0.0
    return passed / total


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default


def compute_quality_metrics(
    prediction: Dict[str, Any],
    before_results: Dict[str, Any],
    after_results: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Computes:
    - pass_rate_before, pass_rate_after
    - avg_time_before, avg_time_after
    - pass_rate_delta, latency_delta
    - regression detection (NONE/MINOR/MAJOR)
    - healing_accuracy (after pass rate)
    - reliability_score
    - healing_effect (IMPROVED/NO_CHANGE/DEGRADED)
    """

    # BEFORE stats
    total_before = int((before_results or {}).get("total_tests", 0) or 0)
    passed_before = int((before_results or {}).get("passed_tests", 0) or 0)
    avg_time_before = _safe_float((before_results or {}).get("avg_exec_time", 0.0), 0.0)

    # AFTER stats
    total_after = int((after_results or {}).get("total_tests", 0) or 0)
    passed_after = int((after_results or {}).get("passed_tests", 0) or 0)
    avg_time_after = _safe_float((after_results or {}).get("avg_exec_time", 0.0), 0.0)

    pass_rate_before = _safe_rate(passed_before, total_before)
    pass_rate_after = _safe_rate(passed_after, total_after)

    pass_rate_delta = pass_rate_after - pass_rate_before
    latency_delta = avg_time_after - avg_time_before

    # Healing effect classification
    if pass_rate_delta > 0.0001:
        healing_effect = "IMPROVED"
    elif pass_rate_delta < -0.0001:
        healing_effect = "DEGRADED"
    else:
        healing_effect = "NO_CHANGE"

    # Regression rules (tunable thresholds)
    # - Degraded pass-rate is always a regression
    # - Latency increase alone can also indicate regression
    regression_impact = "NONE"
    has_regression = False

    # MAJOR thresholds
    if pass_rate_delta <= -0.20 or latency_delta >= 2.0:
        regression_impact = "MAJOR"
        has_regression = True
    # MINOR thresholds
    elif pass_rate_delta <= -0.10 or latency_delta >= 1.0:
        regression_impact = "MINOR"
        has_regression = True

    # Healing accuracy in this system = after pass rate
    healing_accuracy = pass_rate_after

    # Keep recovery_latency for backward compatibility; reflect only positive latency increase
    recovery_latency = max(latency_delta, 0.0)

    # Reliability score:
    # - primarily from healed stability (pass rate)
    # - penalize predicted failure risk
    # - penalize regressions explicitly
    p_fail = _safe_float(prediction.get("p_fail", 0.5), 0.5)
    base = healing_accuracy * 100.0 - p_fail * 20.0

    # Explicit penalty for regressions (so regression can dominate recommendation)
    if regression_impact == "MINOR":
        base -= 10.0
    elif regression_impact == "MAJOR":
        base -= 25.0

    reliability_score = max(0.0, min(100.0, base))

    return {
        "pass_rate_before": pass_rate_before,
        "pass_rate_after": pass_rate_after,
        "pass_rate_delta": pass_rate_delta,
        "avg_time_before": avg_time_before,
        "avg_time_after": avg_time_after,
        "latency_delta": latency_delta,
        "healing_effect": healing_effect,
        "healing_accuracy": healing_accuracy,
        "recovery_latency": recovery_latency,
        "reliability_score": reliability_score,
        "has_regression": has_regression,
        "regression_impact": regression_impact,
        # helpful for debugging / dashboards
        "before_total": total_before,
        "before_passed": passed_before,
        "after_total": total_after,
        "after_passed": passed_after,
    }