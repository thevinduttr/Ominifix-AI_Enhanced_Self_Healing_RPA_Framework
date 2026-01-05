# app/core/test_generator.py

"""
AST-based test generation for healed scripts.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, List, Set


def _find_functions_using_locator(source_code: str, locator: str) -> Set[str]:
    tree = ast.parse(source_code)
    functions: Set[str] = set()

    class LocatorVisitor(ast.NodeVisitor):
        def __init__(self, target: str) -> None:
            self.target = target
            self.current_func: str | None = None

        def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
            prev = self.current_func
            self.current_func = node.name
            self.generic_visit(node)
            self.current_func = prev

        def visit_Constant(self, node: ast.Constant) -> Any:
            if (
                isinstance(node.value, str)
                and self.current_func is not None
                and self.target in node.value
            ):
                functions.add(self.current_func)

    LocatorVisitor(locator).visit(tree)
    return functions


def generate_validation_tests(healing_event: Dict[str, Any]) -> List[Dict[str, Any]]:
    healing_summary = healing_event.get("healing_summary", {}) or {}
    script_output = healing_event.get("script_output", {}) or {}

    healed_script_path = script_output.get("healed_script_path")
    if not healed_script_path:
        return [
            {
                "id": "TC_SMOKE_MAIN_FLOW",
                "description": "Run main RPA flow end-to-end after healing.",
                "priority": "HIGH",
                "script_path": "<unknown>",
            }
        ]

    script_path = Path(healed_script_path)
    try:
        source = script_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        source = ""

    new_locator = str(healing_summary.get("new_locator") or "")
    func_names = (
        _find_functions_using_locator(source, new_locator) if new_locator else set()
    )

    tests: List[Dict[str, Any]] = []

    tests.append(
        {
            "id": "TC_SMOKE_MAIN_FLOW",
            "description": "Run main RPA flow end-to-end after healing.",
            "priority": "HIGH",
            "script_path": str(script_path),
        }
    )

    for fn in sorted(func_names):
        tests.append(
            {
                "id": f"TC_LOCATOR_FUNC_{fn}",
                "description": f"Exercise function '{fn}' that uses the healed locator.",
                "priority": "HIGH",
                "script_path": str(script_path),
                "function_name": fn,
                "locator_under_test": new_locator,
            }
        )

    if not func_names and new_locator:
        tests.append(
            {
                "id": "TC_LOCATOR_REGION",
                "description": "Execute script focusing on region around healed locator.",
                "priority": "MEDIUM",
                "script_path": str(script_path),
                "locator_under_test": new_locator,
            }
        )

    return tests


def build_validation_steps_for_report(tests: List[Dict[str, Any]]) -> List[str]:
    steps: List[str] = []
    for t in tests:
        fn = t.get("function_name")
        if fn:
            steps.append(
                f"Execute {t['id']}: call function '{fn}' in '{t['script_path']}'."
            )
        else:
            steps.append(f"Execute {t['id']}: {t['description']}")
    return steps
