import glob
import os
import runpy
from pathlib import Path

BOT_ID = os.getenv("BOT_ID", "RPA-0020").strip() or "RPA-0020"
USE_HEALED_SCRIPT = os.getenv("USE_HEALED_SCRIPT", "true").strip().lower() in {"1", "true", "yes"}
HEALED_SCRIPTS_DIR = os.getenv("HEALED_SCRIPTS_DIR", "/app/healed_scripts").strip() or "/app/healed_scripts"
ORIGINAL_SCRIPT = os.getenv("ORIGINAL_BOT_SCRIPT", "/app/rpa/form_filler_bot.py").strip() or "/app/rpa/form_filler_bot.py"


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
    ]
    return any(marker in text for marker in markers)


def run_script(path: str) -> None:
    runpy.run_path(path, run_name="__main__")


def main() -> None:
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
