from dataclasses import dataclass
from datetime import datetime
import uuid


# PP1 scope: we support patching selectors inside these calls
SUPPORTED_ACTIONS = {"click", "fill", "wait_for_selector", "query_selector_all", "locator"}

HEALABLE_ERRORS = {
    "ELEMENT_NOT_FOUND",
    "TIMEOUT_WAITING_FOR_SELECTOR",
    "STRICT_MODE_VIOLATION",
    "DETACHED_FROM_DOM",
    "NOT_VISIBLE",
    "NOT_ENABLED",
}

# -- Input normalization maps --------------------------------------------------
# The Element Locator Engine dashboard may use different action / error names.
# Map them to internal Playwright-based identifiers so the pipeline accepts them.

ACTION_ALIASES: dict[str, str] = {
    "locate_element": "locator",
    "locate": "locator",
    "find_element": "locator",
    "select": "click",
}

ERROR_ALIASES: dict[str, str] = {
    "UI_SELECTOR_CHANGED": "ELEMENT_NOT_FOUND",
    "SELECTOR_CHANGED": "ELEMENT_NOT_FOUND",
    "SELECTOR_NOT_FOUND": "ELEMENT_NOT_FOUND",
}


def normalize_action(raw: str) -> str:
    """Map upstream action names to internal Playwright method names."""
    action = (raw or "").strip().lower()
    return ACTION_ALIASES.get(action, action)


def normalize_error(raw: str) -> str:
    """Map upstream error names to internal healable error types."""
    error = (raw or "").strip().upper()
    return ERROR_ALIASES.get(error, error)


@dataclass
class NoFix:
    reason: str


def decide(inp: dict) -> NoFix | None:
    fc = inp.get("failure_context", {})
    action = normalize_action(fc.get("action") or "")
    error = normalize_error(fc.get("error_type") or "")
    dom = inp.get("dom_context", {})

    if action and action not in SUPPORTED_ACTIONS:
        return NoFix(
            f"Action '{action}' not supported in PP1 scope "
            f"(supported: {sorted(SUPPORTED_ACTIONS)})."
        )

    if error and error not in HEALABLE_ERRORS:
        return NoFix(f"Error type '{error}' not healable by locator patching.")

    if not dom.get("new_element_html"):
        return NoFix("Missing dom_context.new_element_html; cannot regenerate locator.")

    return None


def base_output(inp: dict) -> dict:
    md = inp.get("metadata") or {}
    fc = inp.get("failure_context") or {}
    dom = inp.get("dom_context") or {}
    exp = inp.get("element_expectation") or {}

    return {
        "metadata": {
            "healing_id": f"HEAL-{uuid.uuid4()}",
            "report_id": md.get("report_id", ""),
            "run_id": md.get("run_id", ""),
            "bot_id": md.get("bot_id", "UNKNOWN_BOT"),
            "timestamp": datetime.now().isoformat(),
            "source_component": "code_healing_engine",
            "target_component": md.get("target_component", "predictive_testing_engine"),
        },
        "failure_context": {
            "script_path": fc.get("script_path", ""),
            "failing_line": fc.get("failing_line", -1),
            "action": fc.get("action", ""),
            "old_locator": fc.get("old_locator", ""),
            "error_type": fc.get("error_type", ""),
            "error_message": fc.get("error_message", ""),
        },
        "dom_context": {
            "page_url": dom.get("page_url", ""),
            "page_name": dom.get("page_name", ""),
            "new_element_html": dom.get("new_element_html", ""),
        },
        "element_expectation": {
            "expected_role": exp.get("expected_role", ""),
            "expected_text": exp.get("expected_text", ""),
        },
        "element_candidate": inp.get("element_candidate") if inp.get("element_candidate") else None,
        "healing_summary": {
            "status": "NO_FIX",
            "strategy_used": "NO_FIX",
            "action": normalize_action(fc.get("action") or ""),
            "old_locator": fc.get("old_locator", ""),
            "new_locator": "",
            "confidence": 0.0,
            "patcher": "N/A",
            "validation": {"valid": True, "reason": ""},
        },
        "script_output": {
            "original_script_path": "",
            "healed_script_path": "",
        },
        "model_info": {
            "model": "strategy_selector_v1",
            "confidence": 0.0,
        },
    }
