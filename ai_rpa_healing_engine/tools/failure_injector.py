"""
Failure Injector — Controlled Locator Corruption for Research Validation

Takes an RPA script and deliberately corrupts a specified locator to trigger
a Playwright failure. This enables controlled, reproducible testing of the
healing engine.

What it does:
  1. Reads the original RPA script
  2. Finds the locator string on a target line (or auto-detects locator lines)
  3. Corrupts the locator by appending a _BROKEN_ suffix
  4. Saves the broken script to data/scripts/broken/
  5. Generates a corresponding ELR input JSON for the healing engine

Usage:
    python -m tools.failure_injector \\
        --script data/scripts/original/search_flow.py \\
        --line 15 \\
        --locator "textarea[name='q']"

    # Auto-detect mode (finds all locator lines):
    python -m tools.failure_injector \\
        --script data/scripts/original/search_flow.py \\
        --auto
"""

import argparse
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional


# ──────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────

BROKEN_SCRIPTS_DIR = Path("data/scripts/broken")
ELR_OUTPUT_DIR = Path("data/inbox/elr_inputs")
BROKEN_SUFFIX = "_BROKEN_"

# Playwright calls that use locators
LOCATOR_CALL_PATTERNS = [
    # page.fill("selector", ...), page.click("selector"), page.locator("selector")
    re.compile(
        r'(page\.(fill|click|type|press|check|uncheck|hover|dblclick|tap|'
        r'wait_for_selector|query_selector|query_selector_all|locator))\s*\(\s*'
        r'(["\'])(.+?)\3',
        re.IGNORECASE,
    ),
    # page.locator("selector").click() / .fill() etc.
    re.compile(
        r'(page\.locator)\s*\(\s*(["\'])(.+?)\2',
        re.IGNORECASE,
    ),
]

# Map Playwright method to action name
METHOD_TO_ACTION = {
    "fill": "fill",
    "click": "click",
    "type": "fill",
    "press": "fill",
    "check": "click",
    "uncheck": "click",
    "hover": "click",
    "dblclick": "click",
    "tap": "click",
    "wait_for_selector": "wait_for_selector",
    "query_selector": "locator",
    "query_selector_all": "locator",
    "locator": "locator",
}


# ──────────────────────────────────────────────────────────
# Locator Line Detection
# ──────────────────────────────────────────────────────────

def detect_locator_lines(script_path: Path) -> list[dict]:
    """
    Scan a Python script for lines containing Playwright locator calls.

    Returns:
        List of dicts with keys: line_number, locator, action, original_line
    """
    lines = script_path.read_text(encoding="utf-8").splitlines()
    results = []

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue

        for pattern in LOCATOR_CALL_PATTERNS:
            match = pattern.search(line)
            if match:
                groups = match.groups()
                # Extract locator value and method name
                if len(groups) == 4:
                    method = groups[1].lower()
                    locator = groups[3]
                elif len(groups) == 3:
                    method = "locator"
                    locator = groups[2]
                else:
                    continue

                action = METHOD_TO_ACTION.get(method, "locator")
                results.append({
                    "line_number": i,
                    "locator": locator,
                    "action": action,
                    "original_line": line,
                })
                break  # one match per line

    return results


# ──────────────────────────────────────────────────────────
# Locator Corruption
# ──────────────────────────────────────────────────────────

def corrupt_locator(locator: str) -> str:
    """
    Corrupt a locator string so it will fail at runtime.

    Strategy:
      - Append '_BROKEN_YYYYMMDD' to the selector value
      - This makes the selector unmatchable on the real page

    Examples:
      "#btn-submit"                → "#btn-submit_BROKEN_20260305"
      "textarea[name='q']"         → "textarea[name='q_BROKEN_20260305']"
      "[aria-label='Search']"      → "[aria-label='Search_BROKEN_20260305']"
    """
    date_tag = datetime.now().strftime("%Y%m%d")
    suffix = f"{BROKEN_SUFFIX}{date_tag}"

    # If locator has quotes inside (attribute selector), inject before closing quote
    # e.g., textarea[name='q'] → textarea[name='q_BROKEN_20260305']
    inner_quote_match = re.search(r"""(['"]).+?\1""", locator)
    if inner_quote_match:
        # Find the last quote-bounded value and inject before closing
        def inject_suffix(m):
            val = m.group(0)
            return val[:-1] + suffix + val[-1]

        # Apply to the LAST attribute value
        parts = list(re.finditer(r"""['"](.*?)['"]""", locator))
        if parts:
            last_match = parts[-1]
            corrupted = (
                locator[:last_match.end() - 1]
                + suffix
                + locator[last_match.end() - 1:]
            )
            return corrupted

    # Simple selector (id, tag.class, etc.) — just append
    return locator + suffix


def inject_failure(
    script_path: Path,
    target_line: int,
    target_locator: str,
    output_dir: Optional[Path] = None,
) -> dict:
    """
    Inject a failure into an RPA script by corrupting a locator.

    Args:
        script_path: Path to the original RPA script.
        target_line: Line number containing the locator to corrupt.
        target_locator: The locator string to corrupt.
        output_dir: Where to save the broken script (default: data/scripts/broken/).

    Returns:
        dict with keys:
          - broken_script_path: Path to the corrupted script
          - elr_input_path: Path to the generated ELR JSON
          - original_locator: The original locator string
          - corrupted_locator: The corrupted locator string
          - target_line: The target line number
    """
    if output_dir is None:
        output_dir = BROKEN_SCRIPTS_DIR

    output_dir.mkdir(parents=True, exist_ok=True)

    # Read original script
    content = script_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    if target_line < 1 or target_line > len(lines):
        raise ValueError(
            f"Target line {target_line} out of range (script has {len(lines)} lines)"
        )

    # Corrupt the locator on the target line
    original_line = lines[target_line - 1]
    corrupted_locator = corrupt_locator(target_locator)

    if target_locator not in original_line:
        raise ValueError(
            f"Locator '{target_locator}' not found on line {target_line}:\n"
            f"  {original_line}"
        )

    corrupted_line = original_line.replace(target_locator, corrupted_locator, 1)
    lines[target_line - 1] = corrupted_line

    # Write broken script
    stem = script_path.stem
    broken_filename = f"{stem}_broken.py"
    broken_path = output_dir / broken_filename
    broken_path.write_text("\n".join(lines), encoding="utf-8")

    # Detect the action for this line
    action = "click"
    for pattern in LOCATOR_CALL_PATTERNS:
        match = pattern.search(original_line)
        if match:
            groups = match.groups()
            if len(groups) == 4:
                method = groups[1].lower()
            else:
                method = "locator"
            action = METHOD_TO_ACTION.get(method, "locator")
            break

    # Generate ELR input JSON
    elr = _generate_elr_input(
        script_path=str(broken_path),
        failing_line=target_line,
        old_locator=corrupted_locator,
        action=action,
        original_locator=target_locator,
    )

    # Save ELR JSON
    bot_id = f"BOT-INJECT-{stem.upper()}"
    date_str = datetime.now().strftime("%Y-%m-%d")
    ts_str = datetime.now().strftime("%Y%m%d--%H%M%S")

    elr_dir = ELR_OUTPUT_DIR / bot_id / date_str
    elr_dir.mkdir(parents=True, exist_ok=True)
    elr_path = elr_dir / f"elr_input--{ts_str}.json"
    elr_path.write_text(json.dumps(elr, indent=2), encoding="utf-8")

    result = {
        "broken_script_path": str(broken_path),
        "elr_input_path": str(elr_path),
        "original_locator": target_locator,
        "corrupted_locator": corrupted_locator,
        "target_line": target_line,
        "action": action,
        "bot_id": bot_id,
    }

    return result


def _generate_elr_input(
    script_path: str,
    failing_line: int,
    old_locator: str,
    action: str,
    original_locator: str,
) -> dict:
    """Generate a full ELR input JSON for the healing engine."""
    now = datetime.now()
    return {
        "metadata": {
            "schema_version": "1.0",
            "bot_id": f"BOT-INJECT-{Path(script_path).stem.upper()}",
            "run_id": f"inject-{now.strftime('%Y%m%d-%H%M%S')}",
            "timestamp": now.isoformat(),
            "source_component": "failure_injector",
            "target_component": "code_healing_engine",
        },
        "failure_context": {
            "script_path": script_path,
            "failing_line": failing_line,
            "action": action,
            "old_locator": old_locator,
            "error_type": "ELEMENT_NOT_FOUND",
            "error_message": (
                f"Timeout 30000ms exceeded while waiting for selector "
                f"'{old_locator}'. Original locator was '{original_locator}'"
            ),
        },
        "dom_context": {
            "page_url": "",
            "page_name": "",
            "new_element_html": "",
            "_note": (
                "DOM context must be filled manually or by running the bot "
                "against the live page. The healing engine needs the updated "
                "element HTML to generate new locator candidates."
            ),
        },
    }


# ──────────────────────────────────────────────────────────
# Batch Injection (Auto Mode)
# ──────────────────────────────────────────────────────────

def inject_all_locators(script_path: Path) -> list[dict]:
    """
    Auto-detect all locator lines in a script and inject failures for each.

    Returns a list of injection results (one per locator found).
    """
    locator_lines = detect_locator_lines(script_path)

    if not locator_lines:
        print(f"[WARN] No locator lines detected in {script_path}")
        return []

    results = []
    for info in locator_lines:
        try:
            result = inject_failure(
                script_path=script_path,
                target_line=info["line_number"],
                target_locator=info["locator"],
            )
            results.append(result)
            print(
                f"  [OK] Line {info['line_number']}: "
                f"'{info['locator']}' → '{result['corrupted_locator']}'"
            )
        except Exception as e:
            print(f"  [ERR] Line {info['line_number']}: {e}")

    return results


# ──────────────────────────────────────────────────────────
# CLI Entry Point
# ──────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Inject controlled failures into RPA scripts for testing"
    )
    ap.add_argument(
        "--script", required=True,
        help="Path to the original RPA script"
    )
    ap.add_argument(
        "--line", type=int, default=0,
        help="Line number of the locator to corrupt (0 = auto-detect)"
    )
    ap.add_argument(
        "--locator", type=str, default="",
        help="The locator string to corrupt (required if --line is set)"
    )
    ap.add_argument(
        "--auto", action="store_true",
        help="Auto-detect all locator lines and inject failures for each"
    )
    args = ap.parse_args()

    script_path = Path(args.script)
    if not script_path.exists():
        print(f"[ERROR] Script not found: {script_path}")
        return

    print("=" * 60)
    print("FAILURE INJECTOR")
    print("=" * 60)
    print(f"Script: {script_path}")

    if args.auto:
        # Auto mode: detect and inject all locators
        print("[MODE] Auto-detect all locator lines\n")
        locators = detect_locator_lines(script_path)
        print(f"[INFO] Found {len(locators)} locator line(s):")
        for loc in locators:
            print(f"  Line {loc['line_number']:4d}: {loc['action']:20s} → '{loc['locator']}'")

        print(f"\n[INFO] Injecting failures...")
        results = inject_all_locators(script_path)

        print(f"\n[DONE] {len(results)} failure(s) injected")
        for r in results:
            print(f"  Broken script: {r['broken_script_path']}")
            print(f"  ELR input:     {r['elr_input_path']}")

    elif args.line > 0 and args.locator:
        # Targeted mode: corrupt specific locator on specific line
        print(f"[MODE] Targeted injection (line {args.line})\n")
        result = inject_failure(
            script_path=script_path,
            target_line=args.line,
            target_locator=args.locator,
        )
        print(f"[OK] Locator corrupted:")
        print(f"  Original:       '{result['original_locator']}'")
        print(f"  Corrupted:      '{result['corrupted_locator']}'")
        print(f"  Broken script:  {result['broken_script_path']}")
        print(f"  ELR input:      {result['elr_input_path']}")

    else:
        # Scan mode: just show what would be injected
        print("[MODE] Scan only (use --auto to inject, or --line + --locator)\n")
        locators = detect_locator_lines(script_path)
        if not locators:
            print("[WARN] No Playwright locator calls detected")
        else:
            print(f"[INFO] Found {len(locators)} locator line(s):")
            for loc in locators:
                print(f"  Line {loc['line_number']:4d}: {loc['action']:20s} → '{loc['locator']}'")
            print(f"\n[TIP] Run with --auto to inject failures for all, or:")
            print(f"       --line <N> --locator '<selector>' for targeted injection")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
