"""
Cleanup script for Omnifix Healing Engine demos.

This script clears ONLY runtime-generated artifacts so that
a demo starts from a clean state and newly generated files
are clearly visible.

Safe to run before every demo.
"""

import shutil
from pathlib import Path


# -------------------------
# FOLDERS TO CLEAN
# -------------------------
FOLDERS_TO_CLEAR = [
    Path("data/ui_outputs"),
    Path("data/synthetic_outputs"),
    Path("data/scripts/healed"),
]

# Optional: clear batch-generated inputs (ONLY if you want)
# Uncomment if needed
# FOLDERS_TO_CLEAR.append(Path("data/synthetic_inputs/batch"))


def clear_folder(folder: Path):
    if not folder.exists():
        print(f"[SKIP] {folder} does not exist")
        return

    for item in folder.iterdir():
        try:
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        except Exception as e:
            print(f"[WARN] Failed to remove {item}: {e}")

    print(f"[OK] Cleared: {folder}")


def main():
    print("=== Omnifix Demo Cleanup ===")
    for folder in FOLDERS_TO_CLEAR:
        clear_folder(folder)
    print("=== Cleanup completed ===")


if __name__ == "__main__":
    main()
