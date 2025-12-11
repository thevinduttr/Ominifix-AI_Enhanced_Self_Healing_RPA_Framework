# app/core/data_collector.py

"""
data_collector.py

Responsible for:
- Collecting any additional context required for PTQA
  (execution logs, historical metrics, DOM diffs, etc.)

Current version returns a minimal stub context that you can later
replace with real DB / orchestrator calls.
"""

from typing import Any, Dict


def collect_execution_context(healing_event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich the healing event with any contextual data required
    for feature engineering / testing.

    For now this returns a small stub context.
    """
    script_output = healing_event.get("script_output", {})
    metadata = healing_event.get("metadata", {}) or {}

    context: Dict[str, Any] = {
        "script_id": metadata.get("script_id") or metadata.get("bot_id"),
        "environment": metadata.get("environment", "staging"),
        "original_script_path": script_output.get("original_script_path"),
        "healed_script_path": script_output.get("healed_script_path"),
        # Placeholders for future integration
        "last_n_failures": float(metadata.get("last_n_failures", 0.0)),
        "avg_execution_time_before": 1.0,
        "avg_execution_time_after": 1.0,
    }

    return context
