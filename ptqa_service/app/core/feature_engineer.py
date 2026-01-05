# app/core/feature_engineer.py

"""
feature_engineer.py

Converts healing_event + execution_context into a numeric
feature dict for the ML model.
"""

from typing import Any, Dict


def build_feature_vector(
    healing_event: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, float]:
    healing_summary = healing_event.get("healing_summary", {}) or {}
    model_info = healing_event.get("model_info", {}) or {}

    model_confidence = float(model_info.get("model_confidence", 0.5))

    status = str(healing_summary.get("status", "")).lower()
    is_success_status = 1.0 if status == "success" else 0.0

    old_loc = str(healing_summary.get("old_locator") or "")
    new_loc = str(healing_summary.get("new_locator") or "")
    locator_changed = 1.0 if old_loc != new_loc else 0.0

    strategy_used = str(healing_summary.get("strategy_used") or "")
    is_visual_strategy = 1.0 if "visual" in strategy_used.lower() else 0.0

    last_n_failures = float(context.get("last_n_failures", 0.0))
    avg_before = float(context.get("avg_execution_time_before", 1.0))
    avg_after = float(context.get("avg_execution_time_after", 1.0))

    return {
        "model_confidence": model_confidence,
        "is_success_status": is_success_status,
        "locator_changed": locator_changed,
        "is_visual_strategy": is_visual_strategy,
        "last_n_failures": last_n_failures,
        "avg_exec_time_before": avg_before,
        "avg_exec_time_after": avg_after,
    }
