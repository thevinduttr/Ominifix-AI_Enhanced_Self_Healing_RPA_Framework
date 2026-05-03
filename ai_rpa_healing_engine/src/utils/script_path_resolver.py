import os
from pathlib import Path
import re


REPO_NAME = "Ominifix-AI_Enhanced_Self_Healing_RPA_Framework"


def _existing(path: Path) -> Path | None:
    if path.exists():
        return path.resolve()
    return None


def _find_repo_root() -> Path | None:
    """Best-effort discovery of repo root from this file location."""
    current = Path(__file__).resolve()
    for parent in [current, *current.parents]:
        if parent.name == REPO_NAME:
            return parent
        if (parent / "ai_rpa_healing_engine").exists() and (parent / "distributed_self_healing_orchestrator").exists():
            return parent
    return None


def _repo_relative_candidates(raw: str) -> list[Path]:
    """Build candidate relative paths from Windows or POSIX absolute input."""
    normalized = raw.replace("\\", "/").strip()
    if not normalized:
        return []

    parts = [p for p in normalized.split("/") if p]
    if not parts:
        return []

    # Drop Windows drive token like C:
    if re.match(r"^[A-Za-z]:$", parts[0]):
        parts = parts[1:]

    candidates: list[Path] = []

    # Bot containers run from /app, while the healing engine sees the repo at
    # RPA_ROOT=/workspace. Translate common dummy_bot container paths back to
    # their repo location.
    if parts[0] == "app":
        app_suffix = parts[1:]
        if app_suffix:
            candidates.append(Path("distributed_self_healing_orchestrator", "dummy_bot", *app_suffix))

    # Prefer suffix relative to known repository root anchor.
    if REPO_NAME in parts:
        idx = parts.index(REPO_NAME)
        suffix = parts[idx + 1:]
        if suffix:
            candidates.append(Path(*suffix))

    # Fallback to major top-level folders if repo name is absent.
    top_level_markers = (
        "distributed_self_healing_orchestrator",
        "ai_rpa_healing_engine",
        "ptqa_service",
        "sliit_pdp_rpa",
    )
    for marker in top_level_markers:
        if marker in parts:
            idx = parts.index(marker)
            candidates.append(Path(*parts[idx:]))
            break

    # Last fallback: path minus drive token.
    candidates.append(Path(*parts))

    # Deduplicate while preserving order.
    uniq: list[Path] = []
    seen: set[str] = set()
    for c in candidates:
        key = c.as_posix()
        if key in seen:
            continue
        seen.add(key)
        uniq.append(c)
    return uniq


def resolve_script_path(script_path_from_input: str) -> Path:
    """
    Resolve script_path from ELR input.
    Priority:
    1) Absolute path that exists
    2) Relative path from current working directory
    3) Relative path from env var RPA_ROOT (recommended for integration)
    """
    raw = (script_path_from_input or "").strip()
    p = Path(raw)

    found = _existing(p)
    if found:
        return found

    # Retry using slash-normalized input for cross-OS strings.
    normalized = raw.replace("\\", "/")
    if normalized and normalized != raw:
        found = _existing(Path(normalized))
        if found:
            return found

    rpa_root = os.getenv("RPA_ROOT", "").strip()
    relative_candidates = _repo_relative_candidates(raw)

    if rpa_root:
        root = Path(rpa_root)
        # Backward compatible behavior.
        found = _existing(root / raw)
        if found:
            return found

        for rel in relative_candidates:
            found = _existing(root / rel)
            if found:
                return found

    # Auto-detect repository root and try repo-relative suffixes.
    repo_root = _find_repo_root()
    if repo_root:
        for rel in relative_candidates:
            found = _existing(repo_root / rel)
            if found:
                return found

    return p
