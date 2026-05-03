import glob
import os
import runpy
from pathlib import Path

BOT_ID = os.getenv("BOT_ID", "RPA-0020").strip() or "RPA-0020"
USE_HEALED_SCRIPT = os.getenv("USE_HEALED_SCRIPT", "true").strip().lower() in {"1", "true", "yes"}
HEALED_SCRIPTS_DIR = os.getenv("HEALED_SCRIPTS_DIR", "/app/healed_scripts").strip() or "/app/healed_scripts"
ORIGINAL_SCRIPT = os.getenv("ORIGINAL_BOT_SCRIPT", "/app/rpa/form_filler_bot.py").strip() or "/app/rpa/form_filler_bot.py"


def resolve_runtime_path(path_str: str, *, for_healed_dir: bool = False) -> str:
    """Resolve container-style /app paths when running directly on host."""
    if not path_str:
        return path_str

    path = Path(path_str)
    if path.exists():
        return str(path)

    # Map /app/* to local dummy_bot/* when not running in container.
    if path_str.startswith("/app/"):
        dummy_bot_root = Path(__file__).resolve().parents[1]
        mapped = dummy_bot_root / path_str.removeprefix("/app/")
        if mapped.exists():
            return str(mapped)

    # Healed scripts live outside dummy_bot when running on host.
    if for_healed_dir and path_str == "/app/healed_scripts":
        repo_root = Path(__file__).resolve().parents[3]
        mapped = repo_root / "ai_rpa_healing_engine" / "data" / "outbox" / "healed_scripts"
        if mapped.exists():
            return str(mapped)

    return path_str


def ensure_headless_in_no_display_env() -> None:
    """Prevent headed Playwright launches in containers without X display."""
    if os.name == "nt":
        return

    headless_is_set = "HEADLESS" in os.environ
    has_display = bool(os.getenv("DISPLAY", "").strip())
    if not headless_is_set and not has_display:
        os.environ["HEADLESS"] = "true"
        print("[launcher] DISPLAY is not set and HEADLESS was unset. Forcing HEADLESS=true.")


def find_latest_healed_script() -> str:
    bot_root = Path(HEALED_SCRIPTS_DIR) / BOT_ID
    if not bot_root.exists():
        return ""

    patterns = [
        str(bot_root / "*" / "healed_script--*.py"),
        str(bot_root / "healed_script--*.py"),
    ]

    candidates = []
    for pattern in patterns:
        candidates.extend(glob.glob(pattern))

    if not candidates:
        return ""

    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    for candidate in candidates:
        if healed_script_supports_keepalive(candidate):
            return candidate
    return ""


def healed_script_supports_keepalive(path: str) -> bool:
    """Guardrail: run only healed scripts that keep heartbeats alive after success."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False

    markers = [
        "KEEP_ALIVE_AFTER_SUCCESS",
        "Run succeeded. Entering idle heartbeat mode.",
        "while bot_running:",
    ]
    return any(marker in text for marker in markers)


def run_script(path: str) -> None:
    runpy.run_path(path, run_name="__main__")


def main() -> None:
    global HEALED_SCRIPTS_DIR
    global ORIGINAL_SCRIPT

    HEALED_SCRIPTS_DIR = resolve_runtime_path(HEALED_SCRIPTS_DIR, for_healed_dir=True)
    ORIGINAL_SCRIPT = resolve_runtime_path(ORIGINAL_SCRIPT)

    ensure_headless_in_no_display_env()

    if USE_HEALED_SCRIPT:
        healed_path = find_latest_healed_script()
        if healed_path:
            print(f"[launcher] Running healed script for {BOT_ID}: {healed_path}")
            try:
                run_script(healed_path)
                return
            except Exception as exc:
                print(f"[launcher] Healed script failed, falling back to original. Error: {exc}")
        else:
            print(
                f"[launcher] No keepalive-compatible healed script found for {BOT_ID} in {HEALED_SCRIPTS_DIR}. "
                "Using original script."
            )
    else:
        print("[launcher] USE_HEALED_SCRIPT=false. Using original script.")

    print(f"[launcher] Running original script: {ORIGINAL_SCRIPT}")
    run_script(ORIGINAL_SCRIPT)


if __name__ == "__main__":
    main()
