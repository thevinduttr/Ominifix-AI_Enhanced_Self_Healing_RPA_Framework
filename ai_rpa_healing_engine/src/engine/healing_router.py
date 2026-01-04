from dataclasses import dataclass
from datetime import datetime
import uuid


SUPPORTED_ACTIONS = {"click", "fill"}
HEALABLE_ERRORS = {
    "ELEMENT_NOT_FOUND",
    "TIMEOUT_WAITING_FOR_SELECTOR",
    "STRICT_MODE_VIOLATION",
    "DETACHED_FROM_DOM",
    "NOT_VISIBLE",
    "NOT_ENABLED",
}


@dataclass
class NoFix:
    reason: str


def decide(inp: dict) -> NoFix | None:
    fc = inp.get("failure_context", {})
    action = (fc.get("action") or "").lower()
    error = (fc.get("error_type") or "").upper()
    dom = inp.get("dom_context", {})

    if action not in SUPPORTED_ACTIONS:
        return NoFix(f"Action '{action}' not supported in PP1 scope")

    if error not in HEALABLE_ERRORS:
        return NoFix(f"Error type '{error}' not healable by locator patching")

    if not dom.get("new_element_html"):
        return NoFix("Missing DOM context")

    return None


def base_output(inp: dict):
    md = inp["metadata"]
    fc = inp["failure_context"]

    return {
        "metadata": {
            "healing_id": f"HEAL-{uuid.uuid4()}",
            "bot_id": md["bot_id"],
            "timestamp": datetime.now().isoformat(),
            "source_component": "code_healing_engine",
            "target_component": "predictive_testing_engine"
        },
        "healing_summary": {
            "status": "NO_FIX",
            "strategy_used": "NO_FIX",
            "action": fc.get("action"),
            "old_locator": fc.get("old_locator", ""),
            "new_locator": "",
            "confidence": 0.0,
            "patcher": "N/A",
            "validation": {"valid": True, "reason": ""}
        },
        "script_output": {
            "original_script_path": fc.get("script_path"),
            "healed_script_path": ""
        }
    }
