# app/core/test_runner.py

"""
test_runner.py

Dynamically imports the healed script and executes main / target functions.
"""

import importlib.util
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _load_module_from_path(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create spec for module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def _execute_main_flow(module) -> Tuple[bool, float]:
    start = time.perf_counter()
    try:
        if hasattr(module, "run_main_flow"):
            module.run_main_flow()
        elif hasattr(module, "main"):
            module.main()
        ok = True
    except Exception:
        ok = False
    duration = time.perf_counter() - start
    return ok, duration


def _execute_function(module, function_name: str) -> Tuple[bool, float]:
    start = time.perf_counter()
    try:
        func = getattr(module, function_name)
        func()
        ok = True
    except Exception:
        ok = False
    duration = time.perf_counter() - start
    return ok, duration


def run_regression_suite(
    tests: List[Dict[str, Any]],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    if not tests:
        return {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "avg_exec_time_before": float(context.get("avg_execution_time_before", 1.0)),
            "avg_exec_time_after": float(context.get("avg_execution_time_after", 1.0)),
            "details": [],
        }

    script_path = Path(tests[0]["script_path"])
    module = _load_module_from_path(script_path)

    details: List[Dict[str, Any]] = []
    durations: List[float] = []

    passed = 0
    failed = 0

    for t in tests:
        fn_name = t.get("function_name")
        if fn_name:
            ok, dur = _execute_function(module, fn_name)
        else:
            ok, dur = _execute_main_flow(module)

        durations.append(dur)
        if ok:
            passed += 1
        else:
            failed += 1

        details.append(
            {
                "test_id": t["id"],
                "function_name": fn_name,
                "passed": ok,
                "duration_sec": dur,
            }
        )

    total = passed + failed
    avg_after = sum(durations) / total if total > 0 else 0.0
    avg_before = float(context.get("avg_execution_time_before", avg_after))

    return {
        "total_tests": total,
        "passed_tests": passed,
        "failed_tests": failed,
        "avg_exec_time_before": avg_before,
        "avg_exec_time_after": avg_after,
        "details": details,
    }
