import csv
from pathlib import Path
from typing import Any, Dict

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DATA_PATH = DATA_DIR / "ptqa_training_data.csv"

CSV_HEADER = [
    "healing_id",
    "script_id",
    "environment",
    "model_confidence",
    "is_success_status",
    "locator_changed",
    "is_visual_strategy",
    "last_n_failures",
    "avg_exec_time_before",
    "avg_exec_time_after",
    "total_tests",
    "passed_tests",
    "failed_tests",
    "healing_accuracy",
    "recovery_latency",
    "reliability_score",
    "failed",
]


def _ensure_file_with_header() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_PATH.exists():
        with DATA_PATH.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)


def log_training_sample(
    healing_event: Dict[str, Any],
    prediction: Dict[str, Any],
    test_results: Dict[str, Any],
    metrics: Dict[str, Any],
    label_failed: int,
) -> None:
    """
    Append a training sample row to ptqa_training_data.csv.

    label_failed:
        1 if this healing should be considered "failed" in ground truth,
        0 if considered "successful".
    """
    _ensure_file_with_header()

    metadata = healing_event.get("metadata", {}) or {}
    healing_summary = healing_event.get("healing_summary", {}) or {}

    script_id = metadata.get("script_id") or metadata.get("bot_id") or ""
    environment = metadata.get("environment", "staging")

    model_confidence = float(healing_event.get("model_info", {}).get("model_confidence", 0.5))

    status = healing_summary.get("status", "").lower()
    is_success_status = 1 if status == "success" else 0

    old_loc = str(healing_summary.get("old_locator") or "")
    new_loc = str(healing_summary.get("new_locator") or "")
    locator_changed = 1 if old_loc != new_loc else 0

    strategy_used = healing_summary.get("strategy_used", "") or ""
    is_visual_strategy = 1 if "visual" in strategy_used.lower() else 0

    last_n_failures = float(
        metadata.get("last_n_failures", 0.0)
    )  # or from your history system

    avg_before = float(test_results.get("avg_exec_time_before", 1.0))
    avg_after = float(test_results.get("avg_exec_time_after", 1.0))

    total_tests = int(test_results.get("total_tests", 0))
    passed_tests = int(test_results.get("passed_tests", 0))
    failed_tests = int(test_results.get("failed_tests", 0))

    healing_accuracy = float(metrics.get("healing_accuracy", 0.0))
    recovery_latency = float(metrics.get("recovery_latency", 0.0))
    reliability_score = float(metrics.get("reliability_score", 0.0))

    row = [
        healing_event.get("healing_id", metadata.get("healing_id", "")),
        script_id,
        environment,
        model_confidence,
        is_success_status,
        locator_changed,
        is_visual_strategy,
        last_n_failures,
        avg_before,
        avg_after,
        total_tests,
        passed_tests,
        failed_tests,
        healing_accuracy,
        recovery_latency,
        reliability_score,
        int(label_failed),
    ]

    with DATA_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(row)
