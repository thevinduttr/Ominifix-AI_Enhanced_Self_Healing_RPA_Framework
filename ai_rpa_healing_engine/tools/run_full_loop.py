"""
Run Full Loop — End-to-End Self-Healing Integration Demo

The flagship integration tool demonstrating the complete self-healing cycle:
  1. Load an ELR input JSON (failure report)
  2. Parse the failure context
  3. Run the healing engine
  4. Validate the healed output
  5. Log full results with timing

This is the "one-command" proof-of-concept that demonstrates the
entire OmniiFix self-healing pipeline works end-to-end.

Usage:
    # Single ELR input:
    python -m tools.run_full_loop --input data/synthetic_inputs/elr_input_search_01.json

    # Batch all ELRs in a folder:
    python -m tools.run_full_loop --batch data/synthetic_inputs/

    # With verbose output:
    python -m tools.run_full_loop --input <file> --verbose
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analyzer.failure_analyzer import FailureAnalyzer
from src.engine.healing_router import decide, base_output
from src.locator_gen.locator_generator import LocatorGenerator
from src.ml.strategy_predictor import StrategyPredictor
from src.patcher.libcst_patcher import ScriptPatcher
from src.engine.healing_validator import HealingValidator
from src.utils.path_manager import PathManager
from src.utils.script_path_resolver import resolve_script_path


# ──────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────

MODEL_PATH = Path("models/strategy_selector_v1.pkl")
RESULTS_DIR = Path("data/results")
MIN_CONFIDENCE_AGGRESSIVE = 0.70
MIN_CONFIDENCE_CONSERVATIVE = 0.50


# ──────────────────────────────────────────────────────────
# Data Structures
# ──────────────────────────────────────────────────────────

class LoopResult:
    """Holds the complete result of one full-loop execution."""

    def __init__(self):
        self.run_id: str = ""
        self.input_elr: str = ""
        self.bot_id: str = ""
        self.original_status: str = "UNKNOWN"
        self.healing_status: str = "UNKNOWN"
        self.post_healing_status: str = "UNKNOWN"
        self.strategy_used: str = ""
        self.ml_confidence: float = 0.0
        self.healing_mode: str = ""
        self.old_locator: str = ""
        self.new_locator: str = ""
        self.healed_script_path: str = ""
        self.original_script_path: str = ""
        self.error_type: str = ""
        self.time_to_heal_ms: int = 0
        self.validation: dict = {}
        self.failure_reason: str = ""
        self.steps: list = []

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "input_elr": self.input_elr,
            "bot_id": self.bot_id,
            "timestamp": datetime.now().isoformat(),
            "original_status": self.original_status,
            "healing_status": self.healing_status,
            "post_healing_status": self.post_healing_status,
            "strategy_used": self.strategy_used,
            "ml_confidence": self.ml_confidence,
            "healing_mode": self.healing_mode,
            "old_locator": self.old_locator,
            "new_locator": self.new_locator,
            "healed_script_path": self.healed_script_path,
            "original_script_path": self.original_script_path,
            "error_type": self.error_type,
            "time_to_heal_ms": self.time_to_heal_ms,
            "validation": self.validation,
            "failure_reason": self.failure_reason,
            "steps": self.steps,
        }


# ──────────────────────────────────────────────────────────
# Core Loop Execution
# ──────────────────────────────────────────────────────────

def run_full_loop(input_path: Path, verbose: bool = False) -> LoopResult:
    """
    Execute the complete self-healing loop for one ELR input.

    Steps:
      1. Load and validate the ELR input JSON
      2. Parse failure context (via FailureAnalyzer if raw trace is present)
      3. Predict healing strategy (ML classifier)
      4. Apply confidence-aware gate
      5. Generate locator candidates
      6. Patch the broken script (LibCST)
      7. Validate the healed script (syntax check)
      8. Log results and timing

    Args:
        input_path: Path to the ELR input JSON file.
        verbose: If True, print detailed step-by-step output.

    Returns:
        LoopResult with complete execution details.
    """
    result = LoopResult()
    result.input_elr = str(input_path)
    start_time = time.perf_counter()

    def log(step: int, message: str, status: str = "OK"):
        entry = {"step": step, "message": message, "status": status}
        result.steps.append(entry)
        if verbose:
            icon = {"OK": "✓", "FAIL": "✗", "SKIP": "⊘", "INFO": "ℹ"}.get(status, "·")
            print(f"  [{icon}] Step {step}: {message}")

    # ───── STEP 1: Load ELR Input ─────
    log(1, f"Loading ELR input: {input_path.name}", "INFO")

    try:
        inp = json.loads(input_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log(1, f"Failed to load ELR input: {e}", "FAIL")
        result.healing_status = "FAILED"
        result.failure_reason = f"Invalid ELR input: {e}"
        result.time_to_heal_ms = int((time.perf_counter() - start_time) * 1000)
        return result

    md = inp.get("metadata", {})
    fc = inp.get("failure_context", {})
    dom = inp.get("dom_context", {})

    result.bot_id = md.get("bot_id", "UNKNOWN_BOT")
    result.run_id = md.get("run_id", f"loop-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    result.error_type = fc.get("error_type", "")
    result.old_locator = fc.get("old_locator", "")
    result.original_status = "FAILED"  # The ELR exists because the bot failed

    log(1, f"Bot: {result.bot_id} | Error: {result.error_type} | Locator: {result.old_locator}")

    # ───── STEP 2: Analyze Failure Context ─────
    log(2, "Analyzing failure context...", "INFO")

    analyzer = FailureAnalyzer()

    # If there's a raw error trace, parse it to enrich the failure context
    raw_trace = fc.get("raw_error_trace", "")
    if raw_trace:
        parsed = analyzer.analyze(raw_trace)
        # Merge parsed fields into failure_context (don't overwrite explicit fields)
        for key in ["error_type", "old_locator", "failing_line", "action"]:
            if not fc.get(key) and parsed.get(key):
                fc[key] = parsed[key]
        log(2, f"Enriched from trace: error={parsed.get('error_type')}, locator={parsed.get('old_locator')}")
    else:
        log(2, "No raw trace — using structured failure_context fields")

    # Validate we have enough context
    if not fc.get("old_locator"):
        log(2, "Missing old_locator — cannot proceed", "FAIL")
        result.healing_status = "FAILED"
        result.failure_reason = "No old_locator in failure_context"
        result.time_to_heal_ms = int((time.perf_counter() - start_time) * 1000)
        return result

    if not dom.get("new_element_html"):
        log(2, "Missing dom_context.new_element_html — cannot generate locators", "FAIL")
        result.healing_status = "NO_FIX"
        result.failure_reason = "No new_element_html in dom_context"
        result.time_to_heal_ms = int((time.perf_counter() - start_time) * 1000)
        return result

    log(2, f"Context validated: line={fc.get('failing_line')}, action={fc.get('action')}")

    # ───── STEP 3: Resolve Script Path ─────
    log(3, "Resolving script path...", "INFO")

    script_path_in = fc.get("script_path", "")
    resolved_script = resolve_script_path(script_path_in)
    result.original_script_path = str(resolved_script)

    if not resolved_script.exists():
        log(3, f"Script not found: {resolved_script} (set RPA_ROOT env var)", "FAIL")
        result.healing_status = "NO_FIX"
        result.failure_reason = f"Script not found: {resolved_script}"
        result.time_to_heal_ms = int((time.perf_counter() - start_time) * 1000)
        return result

    log(3, f"Resolved: {resolved_script}")

    # ───── STEP 4: ML Strategy Prediction ─────
    log(4, "Running ML strategy prediction...", "INFO")

    try:
        predictor = StrategyPredictor(str(MODEL_PATH))
        pred = predictor.predict(
            fc.get("error_type", ""),
            fc.get("old_locator", ""),
            dom.get("new_element_html", ""),
        )
        result.ml_confidence = float(pred.confidence)
        result.strategy_used = pred.label

        log(4, f"Predicted: {pred.label} (confidence: {pred.confidence:.4f})")
    except Exception as e:
        log(4, f"ML prediction failed: {e} — using fallback", "FAIL")
        result.ml_confidence = 0.0
        result.strategy_used = "NO_FIX"
        result.healing_status = "FAILED"
        result.failure_reason = f"ML prediction error: {e}"
        result.time_to_heal_ms = int((time.perf_counter() - start_time) * 1000)
        return result

    # ───── STEP 5: Router Decision Check ─────
    log(5, "Checking healing router decision...", "INFO")

    router_decision = decide(inp)
    if router_decision:
        log(5, f"Router rejected: {router_decision.reason}", "SKIP")
        result.healing_status = "NO_FIX"
        result.failure_reason = f"Router: {router_decision.reason}"
        result.time_to_heal_ms = int((time.perf_counter() - start_time) * 1000)
        return result

    log(5, "Router approved — proceeding with healing")

    # ───── STEP 6: Confidence Gate ─────
    log(6, "Applying confidence-aware gate...", "INFO")

    if pred.confidence >= MIN_CONFIDENCE_AGGRESSIVE:
        result.healing_mode = "aggressive"
        log(6, f"AGGRESSIVE mode ({pred.confidence:.4f} >= {MIN_CONFIDENCE_AGGRESSIVE})")
    elif pred.confidence >= MIN_CONFIDENCE_CONSERVATIVE:
        result.healing_mode = "conservative"
        log(6, f"CONSERVATIVE mode ({pred.confidence:.4f} >= {MIN_CONFIDENCE_CONSERVATIVE})")
    else:
        result.healing_mode = "no_fix"
        log(6, f"NO_FIX — confidence too low ({pred.confidence:.4f} < {MIN_CONFIDENCE_CONSERVATIVE})", "SKIP")
        result.healing_status = "NO_FIX"
        result.failure_reason = f"Confidence {pred.confidence:.4f} below threshold"
        result.time_to_heal_ms = int((time.perf_counter() - start_time) * 1000)
        return result

    # ───── STEP 7: Generate Locator Candidates ─────
    log(7, "Generating locator candidates...", "INFO")

    lg = LocatorGenerator()
    candidates = lg.generate_candidates(dom.get("new_element_html", ""))
    best = lg.pick_best(candidates)

    if not best:
        log(7, "No locator candidates generated", "FAIL")
        result.healing_status = "NO_FIX"
        result.failure_reason = "No locator candidates from DOM"
        result.time_to_heal_ms = int((time.perf_counter() - start_time) * 1000)
        return result

    # Conservative mode: only allow ID-based locators
    selected_locator = best.get("value", "")
    if result.healing_mode == "conservative":
        if not (selected_locator.startswith("#") or "[name=" in selected_locator):
            log(7, f"Conservative: '{selected_locator}' is not ID/name-based — rejecting", "SKIP")
            result.healing_status = "NO_FIX"
            result.failure_reason = f"Conservative mode rejected non-ID locator: {selected_locator}"
            result.time_to_heal_ms = int((time.perf_counter() - start_time) * 1000)
            return result

    result.new_locator = selected_locator
    log(7, f"Best candidate: '{selected_locator}' (score: {best.get('score', 0)}, type: {best.get('type', '')})")
    if verbose and len(candidates) > 1:
        for c in candidates[:5]:
            print(f"       [{c['score']:3d}] {c['type']:5s} → {c['value']}")

    # ───── STEP 8: Patch Script (LibCST) ─────
    log(8, "Patching script with LibCST...", "INFO")

    pm = PathManager(result.bot_id)
    healed_script_path = pm.healed_script_path()

    patcher = ScriptPatcher()
    patch_result = patcher.patch_locator(
        script_path=str(resolved_script),
        output_path=str(healed_script_path),
        failing_line=int(fc.get("failing_line", 0)),
        old_locator=fc.get("old_locator", ""),
        new_locator=selected_locator,
        action=(fc.get("action") or "").strip().lower(),
    )

    if patch_result.status != "SUCCESS":
        log(8, f"Patching failed: {patch_result.message}", "FAIL")
        result.healing_status = "FAILED"
        result.failure_reason = f"Patcher: {patch_result.message}"
        result.time_to_heal_ms = int((time.perf_counter() - start_time) * 1000)
        return result

    result.healed_script_path = str(healed_script_path)
    log(8, f"Patched: {healed_script_path.name}")

    # ───── STEP 9: Validate Healed Script ─────
    log(9, "Validating healed script (syntax check)...", "INFO")

    validator = HealingValidator()
    validation = validator.validate_script(str(healed_script_path))
    result.validation = validation

    if validation.get("valid"):
        log(9, "Syntax validation PASSED")
        result.healing_status = "SUCCESS"
        result.post_healing_status = "HEALED_PENDING_VERIFICATION"
    else:
        log(9, f"Syntax validation FAILED: {validation.get('reason', '')}", "FAIL")
        result.healing_status = "FAILED"
        result.failure_reason = f"Validation: {validation.get('reason', '')}"

    # ───── STEP 10: Calculate Timing ─────
    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
    result.time_to_heal_ms = elapsed_ms
    log(10, f"Total healing time: {elapsed_ms}ms")

    return result


# ──────────────────────────────────────────────────────────
# Batch Mode
# ──────────────────────────────────────────────────────────

def run_batch(input_dir: Path, verbose: bool = False) -> list[dict]:
    """
    Run the full loop on all ELR JSON files in a directory.

    Returns list of LoopResult dicts.
    """
    elr_files = sorted(input_dir.rglob("*.json"))
    if not elr_files:
        print(f"[WARN] No JSON files found in {input_dir}")
        return []

    print(f"[INFO] Found {len(elr_files)} ELR input file(s)")
    print("=" * 70)

    results = []
    success_count = 0
    no_fix_count = 0
    failed_count = 0

    for i, elr_path in enumerate(elr_files, 1):
        print(f"\n[{i}/{len(elr_files)}] {elr_path.name}")
        print("-" * 50)

        loop_result = run_full_loop(elr_path, verbose=verbose)
        result_dict = loop_result.to_dict()
        results.append(result_dict)

        status = loop_result.healing_status
        if status == "SUCCESS":
            success_count += 1
            icon = "✓"
        elif status == "NO_FIX":
            no_fix_count += 1
            icon = "⊘"
        else:
            failed_count += 1
            icon = "✗"

        print(f"  [{icon}] {status} | {loop_result.strategy_used} "
              f"| conf={loop_result.ml_confidence:.2f} "
              f"| {loop_result.time_to_heal_ms}ms")

    # Summary
    total = len(results)
    print(f"\n{'=' * 70}")
    print(f"BATCH SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Total:   {total}")
    print(f"  Success: {success_count} ({success_count/total*100:.1f}%)" if total else "")
    print(f"  NO_FIX:  {no_fix_count} ({no_fix_count/total*100:.1f}%)" if total else "")
    print(f"  Failed:  {failed_count} ({failed_count/total*100:.1f}%)" if total else "")

    return results


# ──────────────────────────────────────────────────────────
# Results Saving
# ──────────────────────────────────────────────────────────

def save_loop_results(results: list[dict], output_path: Optional[Path] = None):
    """Save full loop results to JSON."""
    if output_path is None:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d--%H%M%S")
        output_path = RESULTS_DIR / f"full_loop_results--{ts}.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Compute summary stats
    total = len(results)
    success = sum(1 for r in results if r["healing_status"] == "SUCCESS")
    no_fix = sum(1 for r in results if r["healing_status"] == "NO_FIX")
    failed = total - success - no_fix
    avg_time = (
        sum(r["time_to_heal_ms"] for r in results) / total
        if total > 0
        else 0
    )

    output = {
        "run_timestamp": datetime.now().isoformat(),
        "total_cases": total,
        "summary": {
            "success": success,
            "success_rate": round(success / total, 4) if total else 0,
            "no_fix": no_fix,
            "no_fix_rate": round(no_fix / total, 4) if total else 0,
            "failed": failed,
            "failed_rate": round(failed / total, 4) if total else 0,
            "avg_time_to_heal_ms": round(avg_time),
        },
        "results": results,
    }

    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\n[SAVED] Results: {output_path}")
    return output_path


# ──────────────────────────────────────────────────────────
# CLI Entry Point
# ──────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Run the complete self-healing loop end-to-end"
    )
    ap.add_argument(
        "--input",
        help="Path to a single ELR input JSON file",
    )
    ap.add_argument(
        "--batch",
        help="Path to a directory containing ELR input JSON files",
    )
    ap.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed step-by-step output",
    )
    ap.add_argument(
        "--output",
        help="Output path for results JSON (default: data/results/full_loop_results--<ts>.json)",
    )
    args = ap.parse_args()

    print("=" * 70)
    print("OMINIFIX — FULL SELF-HEALING LOOP")
    print("=" * 70)

    results = []

    if args.input:
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"[ERROR] File not found: {input_path}")
            sys.exit(1)

        print(f"[MODE] Single ELR input: {input_path.name}")
        print("-" * 70)

        loop_result = run_full_loop(input_path, verbose=True)
        result_dict = loop_result.to_dict()
        results.append(result_dict)

        # Print final summary
        print(f"\n{'─' * 70}")
        print(f"RESULT SUMMARY")
        print(f"{'─' * 70}")
        print(f"  Original Status:   {loop_result.original_status}")
        print(f"  Healing Status:    {loop_result.healing_status}")
        print(f"  Post-Heal Status:  {loop_result.post_healing_status}")
        print(f"  Strategy Used:     {loop_result.strategy_used}")
        print(f"  ML Confidence:     {loop_result.ml_confidence:.4f}")
        print(f"  Healing Mode:      {loop_result.healing_mode}")
        print(f"  Old Locator:       {loop_result.old_locator}")
        print(f"  New Locator:       {loop_result.new_locator}")
        print(f"  Healed Script:     {loop_result.healed_script_path}")
        print(f"  Time to Heal:      {loop_result.time_to_heal_ms}ms")

        if loop_result.failure_reason:
            print(f"  Failure Reason:    {loop_result.failure_reason}")

    elif args.batch:
        batch_dir = Path(args.batch)
        if not batch_dir.exists():
            print(f"[ERROR] Directory not found: {batch_dir}")
            sys.exit(1)

        print(f"[MODE] Batch processing: {batch_dir}")
        results = run_batch(batch_dir, verbose=args.verbose)

    else:
        print("[ERROR] Provide --input <file> or --batch <directory>")
        ap.print_help()
        sys.exit(1)

    # Save results
    output_path = Path(args.output) if args.output else None
    if results:
        save_loop_results(results, output_path)

    print(f"\n{'=' * 70}")
    print("FULL LOOP COMPLETE")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
