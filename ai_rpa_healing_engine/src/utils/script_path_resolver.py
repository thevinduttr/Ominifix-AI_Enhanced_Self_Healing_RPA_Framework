import os
from pathlib import Path


def resolve_script_path(script_path_from_input: str) -> Path:
    """
    Resolve script_path from ELR input.
    Priority:
    1) Absolute path that exists
    2) Relative path from current working directory
    3) Relative path from env var RPA_ROOT (recommended for integration)
    """
    p = Path(script_path_from_input)

    if p.is_absolute() and p.exists():
        return p

    if p.exists():
        return p.resolve()

    rpa_root = os.getenv("RPA_ROOT", "").strip()
    if rpa_root:
        candidate = (Path(rpa_root) / script_path_from_input)
        if candidate.exists():
            return candidate.resolve()

    return p
