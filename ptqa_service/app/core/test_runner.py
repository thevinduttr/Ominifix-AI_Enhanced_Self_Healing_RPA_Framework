# app/core/test_runner.py

"""
test_runner.py

Dynamically imports a script and executes main / target functions.
Supports before vs after comparisons by allowing script_path override.

Supports:
- run_main_flow(context) or run_main_flow()
- main(context) or main()
- returning dict {"success": bool, "video_path": "..."} from bots (optional)
"""

from __future__ import annotations

import importlib.util
import time
from inspect import signature
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional


def _load_module_from_path(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Script not found at: {path.resolve()}")

    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create spec for module from {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def _call_with_optional_context(func, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calls func() or func(context) depending on signature.
    Normalises return to dict with "success" and optional "video_path".
    """
    try:
        n_params = len(signature(func).parameters)
    except Exception:
        n_params = 0

    result = func(context) if n_params > 0 else func()

    if isinstance(result, dict):
        return {
            "success": bool(result.get("success", True)),
            "video_path": result.get("video_path"),
        }

    # If the bot returns True/False, treat that as success
    if isinstance(result, bool):
        return {"success": result, "video_path": None}

    # If bot returns None, assume success unless exception occurred
    return {"success": True, "video_path": None}


def _execute_main_flow(module, context: Dict[str, Any]) -> Tuple[bool, float, Optional[str]]:
    start = time.perf_counter()
    video_path: Optional[str] = None
    ok = False

    try:
        if hasattr(module, "run_main_flow"):
            info = _call_with_optional_context(module.run_main_flow, context)
        elif hasattr(module, "main"):
            info = _call_with_optional_context(module.main, context)
        else:
            raise AttributeError("Script has no run_main_flow() or main().")

        ok = bool(info.get("success", False))
        video_path = info.get("video_path")
    except Exception:
        ok = False

    duration = time.perf_counter() - start
    return ok, duration, video_path


def _execute_function(module, function_name: str, context: Dict[str, Any]) -> Tuple[bool, float, Optional[str]]:
    start = time.perf_counter()
    video_path: Optional[str] = None
    ok = False

    try:
        func = getattr(module, function_name)
        info = _call_with_optional_context(func, context)
        ok = bool(info.get("success", False))
        video_path = info.get("video_path")
    except Exception:
        ok = False

    duration = time.perf_counter() - start
    return ok, duration, video_path


def run_regression_suite(
    tests: List[Dict[str, Any]],
    context: Dict[str, Any],
    script_path_override: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes the provided tests against a script.

    If script_path_override is provided, it is used.
    Otherwise, tests[0]["script_path"] is used.

    Returns:
    - total_tests, passed_tests, failed_tests
    - pass_rate
    - avg_exec_time
    - details
    - video_paths
    """

    if not tests:
        return {
            "script_path": script_path_override or None,
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "pass_rate": 0.0,
            "avg_exec_time": 0.0,
            "details": [],
            "video_paths": [],
        }

    script_path_str = script_path_override or str(tests[0].get("script_path", ""))
    script_path = Path(script_path_str)

    module = _load_module_from_path(script_path)

    details: List[Dict[str, Any]] = []
    durations: List[float] = []
    video_paths: List[str] = []

    passed = 0
    failed = 0

    for t in tests:
        fn_name = t.get("function_name")

        # Copy context per test so bots can safely read test metadata
        ctx = dict(context)
        ctx["test_id"] = t.get("id")
        ctx["function_name"] = fn_name
        ctx["script_path_under_test"] = str(script_path)

        if fn_name:
            ok, dur, vpath = _execute_function(module, fn_name, ctx)
        else:
            ok, dur, vpath = _execute_main_flow(module, ctx)

        durations.append(dur)
        if ok:
            passed += 1
        else:
            failed += 1

        if vpath:
            video_paths.append(str(vpath))

        details.append(
            {
                "test_id": t.get("id"),
                "function_name": fn_name,
                "passed": ok,
                "duration_sec": dur,
                "video_path": vpath,
            }
        )

    total = passed + failed
    avg_exec = sum(durations) / total if total > 0 else 0.0
    pass_rate = (passed / total) if total > 0 else 0.0

    return {
        "script_path": str(script_path),
        "total_tests": total,
        "passed_tests": passed,
        "failed_tests": failed,
        "pass_rate": pass_rate,
        "avg_exec_time": avg_exec,
        "details": details,
        "video_paths": video_paths,
    }