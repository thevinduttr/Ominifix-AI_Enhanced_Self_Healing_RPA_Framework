"""
metrics_engine.py

Combines prediction + test results into healing metrics,
including explicit performance regression detection.
"""

from typing import Any, Dict


def compute_quality_metrics(
    prediction: Dict[str, Any],
    test_results: Dict[str, Any],
) -> Dict[str, Any]:
    total = test_results.get("total_tests", 0) or 1
    passed = test_results.get("passed_tests", 0)

    healing_accuracy = passed / total

    before = float(test_results.get("avg_exec_time_before", 1.0))
    after = float(test_results.get("avg_exec_time_after", 1.0))
    recovery_latency = max(after - before, 0.0)

    # Basic regression detection
    if recovery_latency <= 0.05:
        regression_impact = "NONE"
        has_regression = False
    elif recovery_latency <= 0.5:
        regression_impact = "MINOR"
        has_regression = True
    else:
        regression_impact = "MAJOR"
        has_regression = True

    p_fail = float(prediction.get("p_fail", 0.5))

    reliability_score = max(
        0.0,
        min(100.0, healing_accuracy * 100.0 - p_fail * 20.0),
    )

    return {
        "healing_accuracy": healing_accuracy,
        "recovery_latency": recovery_latency,
        "reliability_score": reliability_score,
        "has_regression": has_regression,
        "regression_impact": regression_impact,
    }
