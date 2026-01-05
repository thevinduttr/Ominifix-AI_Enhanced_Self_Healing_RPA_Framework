from datetime import datetime
from typing import Any, Dict

REQUIRED_ROOT_KEYS = {"metadata", "healing_summary", "script_output"}


def ingest_healing_event(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize incoming healing event payload.
    """
    missing = REQUIRED_ROOT_KEYS - set(payload.keys())
    if missing:
        raise ValueError(f"Missing required keys in healing payload: {missing}")

    metadata = payload.get("metadata", {}) or {}
    healing_id = (
        metadata.get("healing_id")
        or metadata.get("id")
        or f"healing-{datetime.utcnow().timestamp()}"
    )

    return {
        "healing_id": str(healing_id),
        "received_at": datetime.utcnow().isoformat(),
        "metadata": metadata,
        "healing_summary": payload.get("healing_summary", {}),
        "script_output": payload.get("script_output", {}),
        "model_info": payload.get("model_info", {}),
        "raw_payload": payload,
    }
