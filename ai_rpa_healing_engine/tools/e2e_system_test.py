"""
===============================================================================
  OmniiFix — Full System End-to-End Integration Test
===============================================================================

Tests the complete self-healing pipeline for multiple RPA bots:
  1. Reads ELR input JSON (failure report from RPA bot)
  2. Runs the healing engine (ML prediction → locator generation → script patching)
  3. Verifies each bot's output is correctly routed and isolated
  4. Validates healed scripts have correct new locators
  5. Shows diff between broken and healed scripts
  6. Produces a structured summary report

Usage:
    cd ai_rpa_healing_engine
    python -m tools.e2e_system_test [--verbose]
"""

import json
import sys
import os
import time
import difflib
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict

# ── Project imports ─────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.runner.heal import heal_one, load_json
from src.locator_gen.locator_generator import LocatorGenerator
from src.ml.strategy_predictor import StrategyPredictor
from src.engine.healing_router import decide
from src.engine.healing_validator import HealingValidator


# ── Configuration ───────────────────────────────────────────────────────

E2E_INPUT_DIR = Path("data/e2e_test/inputs")
E2E_RESULTS_DIR = Path("data/e2e_test/results")
MODEL_PATH = "models/strategy_selector_v1.pkl"


# ── Expected Test Results ───────────────────────────────────────────────

EXPECTED_RESULTS = {
    "BOT-ECOMMERCE-01": {
        "expected_status": "SUCCESS",
        "old_locator": "#submit-order-old",
        "expected_new_locator_contains": "#submit-order",  # ID-based
        "action": "click",
        "description": "E-commerce checkout — submit button ID changed",
    },
    "BOT-HR-PORTAL-01": {
        "expected_status": "SUCCESS",
        "old_locator": "input[name='usr_name_old']",
        "expected_new_locator_contains": "#user-login",  # ID-based
        "action": "fill",
        "description": "HR Portal login — username field name changed",
    },
    "BOT-SLIIT-PDP-01": {
        "expected_status": "SUCCESS",
        "old_locator": "a.nav-link-old[role='tab']",
        "expected_new_locator_contains": "#tab-online",  # ID-based
        "action": "click",
        "description": "SLIIT PDP scraper — tab CSS class changed",
    },
    "BOT-INVENTORY-01": {
        "expected_status": "SUCCESS",
        "old_locator": "#search-box-v1",
        "expected_new_locator_contains": "#search-input",  # ID-based
        "action": "fill",
        "description": "Inventory system — search box ID renamed",
    },
    "BOT-REPORT-01": {
        "expected_status": "SUCCESS",
        "old_locator": "button.download-btn-old",
        "expected_new_locator_contains": "#export-csv",  # ID-based
        "action": "click",
        "description": "Report download — button class changed",
    },
}


# ── Data classes ────────────────────────────────────────────────────────

@dataclass
class BotTestResult:
    bot_id: str = ""
    description: str = ""
    elr_input_file: str = ""
    healing_status: str = ""
    expected_status: str = ""
    status_match: bool = False
    old_locator: str = ""
    new_locator: str = ""
    expected_locator_fragment: str = ""
    locator_correct: bool = False
    strategy_used: str = ""
    ml_confidence: float = 0.0
    healing_mode: str = ""
    healed_script_path: str = ""
    output_json_path: str = ""
    diff_lines: list = field(default_factory=list)
    time_ms: int = 0
    passed: bool = False
    error: str = ""


# ── Utility functions ───────────────────────────────────────────────────

def colorize(text: str, color: str) -> str:
    """Add ANSI color codes if terminal supports it."""
    colors = {
        "green": "\033[92m",
        "red": "\033[91m",
        "yellow": "\033[93m",
        "cyan": "\033[96m",
        "bold": "\033[1m",
        "reset": "\033[0m",
    }
    if os.name == "nt":
        # Enable ANSI on Windows
        os.system("")
    return f"{colors.get(color, '')}{text}{colors.get('reset', '')}"


def compute_diff(broken_path: str, healed_path: str) -> list[str]:
    """Compute unified diff between broken and healed scripts."""
    try:
        broken = Path(broken_path).read_text(encoding="utf-8").splitlines()
        healed = Path(healed_path).read_text(encoding="utf-8").splitlines()
        diff = list(difflib.unified_diff(
            broken, healed,
            fromfile=f"broken/{Path(broken_path).name}",
            tofile=f"healed/{Path(healed_path).name}",
            lineterm="",
        ))
        return diff
    except Exception as e:
        return [f"Error computing diff: {e}"]


def print_header(title: str):
    width = 72
    print()
    print(colorize("=" * width, "cyan"))
    print(colorize(f"  {title}", "bold"))
    print(colorize("=" * width, "cyan"))


def print_section(title: str):
    print(f"\n{colorize('─' * 60, 'cyan')}")
    print(f"  {colorize(title, 'bold')}")
    print(colorize("─" * 60, "cyan"))


# ── Core Test Functions ─────────────────────────────────────────────────

def run_single_bot_test(elr_path: Path, expected: dict, verbose: bool = False) -> BotTestResult:
    """
    Run the full healing pipeline for one bot's failure and validate results.
    """
    result = BotTestResult()
    start = time.perf_counter()

    try:
        # Load the ELR input
        inp = load_json(elr_path)
        bot_id = inp["metadata"]["bot_id"]
        result.bot_id = bot_id
        result.elr_input_file = str(elr_path)
        result.description = expected.get("description", "")
        result.expected_status = expected["expected_status"]
        result.old_locator = inp["failure_context"]["old_locator"]
        result.expected_locator_fragment = expected.get("expected_new_locator_contains", "")

        if verbose:
            print(f"    Bot ID:       {bot_id}")
            print(f"    Script:       {inp['failure_context']['script_path']}")
            print(f"    Error:        {inp['failure_context']['error_type']}")
            print(f"    Old Locator:  {result.old_locator}")
            print(f"    Action:       {inp['failure_context']['action']}")
            print(f"    DOM HTML:     {inp['dom_context']['new_element_html'][:80]}...")

        # ── Run heal_one (the main pipeline) ──
        status = heal_one(elr_path)
        result.healing_status = status

        # ── Find the output JSON ──
        # heal_one writes output to data/outbox/healing_outputs/<bot_id>/<date>/
        outbox = Path("data/outbox/healing_outputs") / bot_id
        if outbox.exists():
            json_files = sorted(outbox.rglob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
            if json_files:
                result.output_json_path = str(json_files[0])
                output_data = load_json(json_files[0])

                hs = output_data.get("healing_summary", {})
                result.strategy_used = hs.get("strategy_used", "")
                result.new_locator = hs.get("new_locator", "")
                result.ml_confidence = output_data.get("model_info", {}).get("confidence", 0.0)
                result.healing_mode = output_data.get("model_info", {}).get("healing_mode", "")

                so = output_data.get("script_output", {})
                result.healed_script_path = so.get("healed_script_path", "")

        # ── Validate status match ──
        result.status_match = (result.healing_status == result.expected_status)

        # ── Validate locator correctness ──
        if result.expected_locator_fragment and result.new_locator:
            result.locator_correct = result.expected_locator_fragment in result.new_locator
        elif result.expected_status == "NO_FIX" and result.healing_status == "NO_FIX":
            result.locator_correct = True  # NO_FIX doesn't need a new locator

        # ── Compute diff if healed script exists ──
        if result.healed_script_path and Path(result.healed_script_path).exists():
            broken_script = inp["failure_context"]["script_path"]
            result.diff_lines = compute_diff(broken_script, result.healed_script_path)

        # ── Overall pass/fail ──
        result.passed = result.status_match and result.locator_correct

    except Exception as e:
        result.healing_status = "ERROR"
        result.error = str(e)
        result.passed = False

    result.time_ms = int((time.perf_counter() - start) * 1000)
    return result


def run_component_verification(elr_path: Path, verbose: bool = False) -> dict:
    """
    Verify each component individually for one ELR input.
    Returns a dict with per-component pass/fail.
    """
    inp = load_json(elr_path)
    fc = inp["failure_context"]
    dom = inp["dom_context"]
    results = {}

    # 1. ML Strategy Predictor
    try:
        predictor = StrategyPredictor(MODEL_PATH)
        pred = predictor.predict(fc["error_type"], fc["old_locator"], dom["new_element_html"])
        results["ml_predictor"] = {
            "status": "OK",
            "strategy": pred.label,
            "confidence": round(float(pred.confidence), 4),
        }
    except Exception as e:
        results["ml_predictor"] = {"status": "FAIL", "error": str(e)}

    # 2. Locator Generator
    try:
        lg = LocatorGenerator()
        candidates = lg.generate_candidates(dom["new_element_html"])
        best = lg.pick_best(candidates)
        results["locator_generator"] = {
            "status": "OK",
            "candidates_count": len(candidates),
            "best_locator": best.get("value", "") if best else "NONE",
            "best_score": best.get("score", 0) if best else 0,
            "best_type": best.get("type", "") if best else "",
        }
    except Exception as e:
        results["locator_generator"] = {"status": "FAIL", "error": str(e)}

    # 3. Healing Router
    try:
        decision = decide(inp)
        results["healing_router"] = {
            "status": "OK",
            "decision": "REJECT" if decision else "APPROVE",
            "reason": decision.reason if decision else "Approved for healing",
        }
    except Exception as e:
        results["healing_router"] = {"status": "FAIL", "error": str(e)}

    # 4. Healing Validator (checks if validator module loads)
    try:
        validator = HealingValidator()
        results["healing_validator"] = {"status": "OK"}
    except Exception as e:
        results["healing_validator"] = {"status": "FAIL", "error": str(e)}

    return results


# ── Main E2E Runner ─────────────────────────────────────────────────────

def run_e2e_test(verbose: bool = False):
    """
    Main entry point: runs the full system test across all bots.
    """
    print_header("OmniiFix — Full System End-to-End Integration Test")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"  Timestamp:   {timestamp}")
    print(f"  Input Dir:   {E2E_INPUT_DIR}")
    print(f"  Model:       {MODEL_PATH}")
    print(f"  Bots:        {len(EXPECTED_RESULTS)}")

    # Discover all ELR input files
    elr_files = sorted(E2E_INPUT_DIR.rglob("*.json"))
    if not elr_files:
        print(colorize("\n  ERROR: No ELR input files found!", "red"))
        sys.exit(1)

    print(f"  ELR Files:   {len(elr_files)}")

    # ────────────────────────────────────────────────────────────────
    # PHASE 1: Component-Level Verification
    # ────────────────────────────────────────────────────────────────
    print_section("PHASE 1: Component-Level Verification")

    all_component_results = {}
    for elr_path in elr_files:
        inp = load_json(elr_path)
        bot_id = inp["metadata"]["bot_id"]
        print(f"\n  [{bot_id}] Verifying components...")

        comp_results = run_component_verification(elr_path, verbose)
        all_component_results[bot_id] = comp_results

        for comp_name, comp_data in comp_results.items():
            status = comp_data["status"]
            icon = colorize("PASS", "green") if status == "OK" else colorize("FAIL", "red")
            detail = ""
            if comp_name == "ml_predictor" and status == "OK":
                detail = f" → {comp_data['strategy']} ({comp_data['confidence']:.4f})"
            elif comp_name == "locator_generator" and status == "OK":
                detail = f" → {comp_data['best_locator']} (score={comp_data['best_score']})"
            elif comp_name == "healing_router" and status == "OK":
                detail = f" → {comp_data['decision']}"
            print(f"    {icon}  {comp_name}{detail}")

    # ────────────────────────────────────────────────────────────────
    # PHASE 2: Full Pipeline Healing Test
    # ────────────────────────────────────────────────────────────────
    print_section("PHASE 2: Full Pipeline Healing (per bot)")

    bot_results: list[BotTestResult] = []
    total_start = time.perf_counter()

    for i, elr_path in enumerate(elr_files, 1):
        inp = load_json(elr_path)
        bot_id = inp["metadata"]["bot_id"]
        expected = EXPECTED_RESULTS.get(bot_id, {})

        if not expected:
            print(colorize(f"\n  [{i}] SKIP: {bot_id} — no expected result defined", "yellow"))
            continue

        print(f"\n  [{i}/{len(elr_files)}] {colorize(bot_id, 'bold')}")
        print(f"    {expected['description']}")

        result = run_single_bot_test(elr_path, expected, verbose)
        bot_results.append(result)

        # Print result
        if result.passed:
            print(f"    Status:     {colorize('PASS', 'green')} (healing={result.healing_status})")
        else:
            print(f"    Status:     {colorize('FAIL', 'red')} (healing={result.healing_status}, expected={result.expected_status})")

        print(f"    Old:        {result.old_locator}")
        print(f"    New:        {result.new_locator or 'N/A'}")
        print(f"    Strategy:   {result.strategy_used}")
        print(f"    Confidence: {result.ml_confidence:.4f}")
        print(f"    Mode:       {result.healing_mode or 'N/A'}")
        print(f"    Time:       {result.time_ms}ms")

        if result.error:
            print(f"    Error:      {colorize(result.error, 'red')}")

    total_time = int((time.perf_counter() - total_start) * 1000)

    # ────────────────────────────────────────────────────────────────
    # PHASE 3: Multi-Bot Routing Verification
    # ────────────────────────────────────────────────────────────────
    print_section("PHASE 3: Multi-Bot Output Routing Verification")

    routing_pass = True
    seen_bots = set()
    for result in bot_results:
        bot_id = result.bot_id
        seen_bots.add(bot_id)

        # Check outputs are in correct bot-specific directories
        if result.output_json_path:
            if bot_id in result.output_json_path:
                print(f"    {colorize('PASS', 'green')}  {bot_id} → output routed to correct directory")
            else:
                print(f"    {colorize('FAIL', 'red')}  {bot_id} → output NOT in bot-specific directory!")
                routing_pass = False
        else:
            print(f"    {colorize('WARN', 'yellow')}  {bot_id} → no output JSON found")

        if result.healed_script_path:
            if bot_id in result.healed_script_path:
                print(f"    {colorize('PASS', 'green')}  {bot_id} → healed script routed correctly")
            else:
                print(f"    {colorize('FAIL', 'red')}  {bot_id} → healed script NOT in bot-specific directory!")
                routing_pass = False

    # Verify all bots are separate (no cross-contamination)
    print(f"\n    Unique bot outputs: {len(seen_bots)}/{len(EXPECTED_RESULTS)}")
    if len(seen_bots) == len(EXPECTED_RESULTS):
        print(f"    {colorize('PASS', 'green')}  All bots handled independently — no cross-contamination")
    else:
        print(f"    {colorize('FAIL', 'red')}  Missing bot outputs!")
        routing_pass = False

    # ────────────────────────────────────────────────────────────────
    # PHASE 4: Diff Analysis
    # ────────────────────────────────────────────────────────────────
    print_section("PHASE 4: Script Diff Analysis (Broken → Healed)")

    for result in bot_results:
        if result.diff_lines:
            print(f"\n  [{result.bot_id}] {result.description}")
            for line in result.diff_lines:
                if line.startswith("---") or line.startswith("+++"):
                    print(f"    {colorize(line, 'bold')}")
                elif line.startswith("-"):
                    print(f"    {colorize(line, 'red')}")
                elif line.startswith("+"):
                    print(f"    {colorize(line, 'green')}")
                elif line.startswith("@@"):
                    print(f"    {colorize(line, 'cyan')}")
                else:
                    print(f"    {line}")
        elif result.healing_status == "SUCCESS":
            print(f"\n  [{result.bot_id}] No diff available (healed script missing)")

    # ────────────────────────────────────────────────────────────────
    # PHASE 5: Healed Script Content Verification
    # ────────────────────────────────────────────────────────────────
    print_section("PHASE 5: Healed Script Content Verification")

    for result in bot_results:
        if result.healed_script_path and Path(result.healed_script_path).exists():
            healed_content = Path(result.healed_script_path).read_text(encoding="utf-8")
            old = result.old_locator
            new = result.new_locator

            # Verify old locator is NOT in healed script
            old_removed = old not in healed_content
            # Verify new locator IS in healed script
            new_present = new in healed_content if new else False

            if old_removed and new_present:
                print(f"    {colorize('PASS', 'green')}  {result.bot_id}: old locator removed, new locator present")
            elif not old_removed:
                print(f"    {colorize('FAIL', 'red')}  {result.bot_id}: old locator '{old}' STILL in healed script!")
            elif not new_present:
                print(f"    {colorize('FAIL', 'red')}  {result.bot_id}: new locator '{new}' NOT found in healed script!")

            # Extra: Validate syntax
            validator = HealingValidator()
            validation = validator.validate_script(result.healed_script_path)
            if validation.get("valid"):
                print(f"    {colorize('PASS', 'green')}  {result.bot_id}: healed script passes syntax check")
            else:
                print(f"    {colorize('FAIL', 'red')}  {result.bot_id}: syntax error: {validation.get('reason')}")

    # ────────────────────────────────────────────────────────────────
    # FINAL SUMMARY
    # ────────────────────────────────────────────────────────────────
    print_header("FINAL SUMMARY")

    passed = sum(1 for r in bot_results if r.passed)
    failed = len(bot_results) - passed
    all_pass = passed == len(bot_results) and routing_pass

    print(f"  Bots Tested:      {len(bot_results)}")
    print(f"  Passed:           {colorize(str(passed), 'green')}")
    print(f"  Failed:           {colorize(str(failed), 'red') if failed else '0'}")
    print(f"  Multi-Bot Route:  {colorize('PASS', 'green') if routing_pass else colorize('FAIL', 'red')}")
    print(f"  Total Time:       {total_time}ms")
    print(f"  Avg Time/Bot:     {total_time // max(len(bot_results), 1)}ms")

    print(f"\n  {'─' * 50}")
    header = f"  {'Bot ID':<22} {'Status':<10} {'Old Locator':<28} {'New Locator':<22} {'Time':<6}"
    print(colorize(header, "bold"))
    print(f"  {'─' * 50}")

    for r in bot_results:
        status_str = colorize("PASS", "green") if r.passed else colorize("FAIL", "red")
        old = r.old_locator[:26] if len(r.old_locator) > 26 else r.old_locator
        new = (r.new_locator[:20] if len(r.new_locator) > 20 else r.new_locator) or "N/A"
        print(f"  {r.bot_id:<22} {status_str:<19} {old:<28} {new:<22} {r.time_ms}ms")

    print()
    if all_pass:
        print(colorize("  ✅ ALL TESTS PASSED — Full system operational", "green"))
    else:
        print(colorize("  ❌ SOME TESTS FAILED — See details above", "red"))

    # ────────────────────────────────────────────────────────────────
    # Save structured report
    # ────────────────────────────────────────────────────────────────
    E2E_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d--%H%M%S")
    report_path = E2E_RESULTS_DIR / f"e2e_report--{ts}.json"

    report = {
        "timestamp": timestamp,
        "summary": {
            "total_bots": len(bot_results),
            "passed": passed,
            "failed": failed,
            "routing_verified": routing_pass,
            "all_pass": all_pass,
            "total_time_ms": total_time,
        },
        "component_verification": all_component_results,
        "bot_results": [
            {
                "bot_id": r.bot_id,
                "description": r.description,
                "passed": r.passed,
                "healing_status": r.healing_status,
                "expected_status": r.expected_status,
                "old_locator": r.old_locator,
                "new_locator": r.new_locator,
                "strategy_used": r.strategy_used,
                "ml_confidence": r.ml_confidence,
                "healing_mode": r.healing_mode,
                "time_ms": r.time_ms,
                "healed_script_path": r.healed_script_path,
                "output_json_path": r.output_json_path,
                "diff_line_count": len(r.diff_lines),
                "error": r.error,
            }
            for r in bot_results
        ],
    }

    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n  Report saved: {report_path}")
    print()

    return 0 if all_pass else 1


# ── CLI ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OmniiFix E2E System Test")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    args = parser.parse_args()

    sys.exit(run_e2e_test(verbose=args.verbose))
