"""
Stress Test — Batch Healing Validation on All Synthetic Cases

Runs the full self-healing pipeline on all 150 synthetic cases and reports:
  - Overall healing success rate (%)
  - Per-strategy success rate
  - Incorrect patch rate (healed but wrong locator)
  - NO_FIX correctness rate
  - Confidence distribution per strategy
  - Average time-to-heal (ms)

Saves full structured output to `data/results/stress_test_results.json`.

Usage:
    python -m tools.stress_test
    python -m tools.stress_test --verbose
    python -m tools.stress_test --include-demo    # also run demo test cases
"""

import argparse
import json
import sys
import time
import statistics
from datetime import datetime
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.locator_gen.locator_generator import LocatorGenerator
from src.ml.strategy_predictor import StrategyPredictor
from src.patcher.libcst_patcher import ScriptPatcher
from src.engine.healing_validator import HealingValidator
from src.engine.healing_router import decide
from src.utils.script_path_resolver import resolve_script_path
from src.analyzer.failure_analyzer import FailureAnalyzer

# ──────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────

MODEL_PATH = Path("models/strategy_selector_v1.pkl")
RESULTS_DIR = Path("data/results")
MIN_CONFIDENCE_AGGRESSIVE = 0.70
MIN_CONFIDENCE_CONSERVATIVE = 0.50


# ──────────────────────────────────────────────────────────
# Stress Test Runner
# ──────────────────────────────────────────────────────────

class StressTestRunner:
    """Runs healing on all synthetic cases and produces comprehensive metrics."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.predictor = StrategyPredictor(str(MODEL_PATH))
        self.locator_gen = LocatorGenerator()
        self.patcher = ScriptPatcher()
        self.analyzer = FailureAnalyzer()

    def run(self, input_dirs: list) -> dict:
        """Run stress test on all ELR JSON files in the given directories."""
        start_time = time.time()

        # Collect all ELR input files
        elr_files = []
        for d in input_dirs:
            p = Path(d)
            if p.is_dir():
                elr_files.extend(sorted(p.glob("*.json")))
            elif p.is_file() and p.suffix == ".json":
                elr_files.append(p)

        total = len(elr_files)
        if total == 0:
            print("[WARN] No ELR input files found.")
            return {}

        print(f"[INFO] Running stress test on {total} cases...")
        print("=" * 70)

        # Counters
        results = []
        outcomes = {"SUCCESS": 0, "NO_FIX": 0, "FAILED": 0}
        strategy_success = defaultdict(lambda: {"total": 0, "success": 0})
        confidence_by_strategy = defaultdict(list)
        heal_times = []
        incorrect_patches = 0
        nofix_correct = 0
        nofix_total = 0

        for idx, elr_file in enumerate(elr_files, 1):
            result = self._process_single(elr_file, idx, total)
            results.append(result)

            outcome = result["outcome"]
            outcomes[outcome] = outcomes.get(outcome, 0) + 1

            strategy = result.get("strategy", "")
            confidence = result.get("confidence", 0.0)
            heal_time = result.get("heal_time_ms", 0)

            if strategy:
                strategy_success[strategy]["total"] += 1
                if outcome == "SUCCESS":
                    strategy_success[strategy]["success"] += 1
                confidence_by_strategy[strategy].append(confidence)

            if outcome == "SUCCESS":
                heal_times.append(heal_time)

            # Track incorrect patches (patched but syntax error)
            if outcome == "FAILED" and result.get("patch_applied", False):
                incorrect_patches += 1

            # Track NO_FIX correctness
            if result.get("expected_nofix", False):
                nofix_total += 1
                if outcome == "NO_FIX":
                    nofix_correct += 1

        total_time = round((time.time() - start_time) * 1000)

        # ── Build metrics ──
        success_rate = (outcomes["SUCCESS"] / total * 100) if total > 0 else 0.0
        nofix_rate = (outcomes["NO_FIX"] / total * 100) if total > 0 else 0.0
        failed_rate = (outcomes["FAILED"] / total * 100) if total > 0 else 0.0
        incorrect_patch_rate = (incorrect_patches / total * 100) if total > 0 else 0.0
        nofix_correctness = (nofix_correct / nofix_total * 100) if nofix_total > 0 else 0.0

        avg_heal_time = round(statistics.mean(heal_times)) if heal_times else 0
        median_heal_time = round(statistics.median(heal_times)) if heal_times else 0
        min_heal_time = min(heal_times) if heal_times else 0
        max_heal_time = max(heal_times) if heal_times else 0

        per_strategy_metrics = {}
        for strat, counts in strategy_success.items():
            confs = confidence_by_strategy.get(strat, [])
            per_strategy_metrics[strat] = {
                "total": counts["total"],
                "success": counts["success"],
                "success_rate": round(counts["success"] / counts["total"] * 100, 1) if counts["total"] > 0 else 0.0,
                "avg_confidence": round(statistics.mean(confs), 4) if confs else 0.0,
                "min_confidence": round(min(confs), 4) if confs else 0.0,
                "max_confidence": round(max(confs), 4) if confs else 0.0,
            }

        # ── Print summary ──
        print()
        print("=" * 70)
        print("STRESS TEST RESULTS")
        print("=" * 70)
        print(f"  Total Cases:            {total}")
        print(f"  SUCCESS:                {outcomes['SUCCESS']} ({success_rate:.1f}%)")
        print(f"  NO_FIX:                 {outcomes['NO_FIX']} ({nofix_rate:.1f}%)")
        print(f"  FAILED:                 {outcomes['FAILED']} ({failed_rate:.1f}%)")
        print(f"  Incorrect Patch Rate:   {incorrect_patches} ({incorrect_patch_rate:.1f}%)")
        print(f"  NO_FIX Correctness:     {nofix_correct}/{nofix_total} ({nofix_correctness:.1f}%)")
        print()
        print("  Time-to-Heal (SUCCESS cases):")
        print(f"    Average:              {avg_heal_time}ms")
        print(f"    Median:               {median_heal_time}ms")
        print(f"    Min:                  {min_heal_time}ms")
        print(f"    Max:                  {max_heal_time}ms")
        print()
        print("  Per-Strategy Breakdown:")
        for strat, m in sorted(per_strategy_metrics.items()):
            print(f"    {strat}:")
            print(f"      Total: {m['total']}  Success: {m['success']}  Rate: {m['success_rate']}%")
            print(f"      Confidence: avg={m['avg_confidence']:.4f}  min={m['min_confidence']:.4f}  max={m['max_confidence']:.4f}")
        print()
        print(f"  Total Execution Time:   {total_time}ms")
        print("=" * 70)

        # ── Save results ──
        output = {
            "run_id": f"STRESS-{datetime.now().strftime('%Y%m%d--%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "total_cases": total,
            "summary": {
                "success": outcomes["SUCCESS"],
                "no_fix": outcomes["NO_FIX"],
                "failed": outcomes["FAILED"],
                "success_rate_pct": round(success_rate, 1),
                "no_fix_rate_pct": round(nofix_rate, 1),
                "failed_rate_pct": round(failed_rate, 1),
                "incorrect_patch_rate_pct": round(incorrect_patch_rate, 1),
                "nofix_correctness_pct": round(nofix_correctness, 1),
            },
            "timing": {
                "avg_heal_time_ms": avg_heal_time,
                "median_heal_time_ms": median_heal_time,
                "min_heal_time_ms": min_heal_time,
                "max_heal_time_ms": max_heal_time,
                "total_execution_time_ms": total_time,
            },
            "per_strategy": per_strategy_metrics,
            "individual_results": results,
        }

        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        out_path = RESULTS_DIR / f"stress_test_results--{datetime.now().strftime('%Y%m%d--%H%M%S')}.json"
        out_path.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
        print(f"[SAVED] {out_path}")

        # Also save a latest copy for easy reference
        latest_path = RESULTS_DIR / "stress_test_results.json"
        latest_path.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
        print(f"[SAVED] {latest_path}")

        return output

    def _process_single(self, elr_file: Path, idx: int, total: int) -> dict:
        """Process one ELR input through the full healing pipeline."""
        start = time.time()
        result = {
            "file": elr_file.name,
            "outcome": "FAILED",
            "strategy": "",
            "confidence": 0.0,
            "heal_time_ms": 0,
            "patch_applied": False,
            "expected_nofix": False,
            "error": "",
        }

        try:
            inp = json.loads(elr_file.read_text(encoding="utf-8"))
        except Exception as e:
            result["error"] = f"Failed to load JSON: {e}"
            self._log(idx, total, elr_file.name, result)
            return result

        # Extract fields
        fc = inp.get("failure_context", {})
        dom = inp.get("dom_context", {})
        error_type = fc.get("error_type", "ELEMENT_NOT_FOUND")
        old_locator = fc.get("old_locator", "")
        action = fc.get("action", "fill")
        failing_line = int(fc.get("failing_line", 0))
        script_path_raw = fc.get("script_path", "")
        element_html = dom.get("new_element_html", "")

        # Check for traceback enrichment
        raw_trace = fc.get("raw_error_trace", "")
        if raw_trace:
            parsed = self.analyzer.analyze(raw_trace)
            if parsed.get("error_type"):
                error_type = parsed["error_type"]
            if parsed.get("old_locator"):
                old_locator = parsed["old_locator"]

        # Check for expected NO_FIX (from _test_meta or empty DOM)
        test_meta = inp.get("_test_meta", {})
        if test_meta.get("expected_outcome") == "NO_FIX":
            result["expected_nofix"] = True
        elif not element_html or not element_html.strip():
            result["expected_nofix"] = True

        # Step 1: Validate DOM context
        if not element_html or not element_html.strip():
            result["outcome"] = "NO_FIX"
            result["error"] = "Empty DOM context"
            result["heal_time_ms"] = round((time.time() - start) * 1000)
            self._log(idx, total, elr_file.name, result)
            return result

        # Step 2: Resolve script path
        try:
            resolved_path = resolve_script_path(script_path_raw)
        except Exception:
            resolved_path = script_path_raw

        # Step 3: ML prediction
        try:
            prediction = self.predictor.predict(error_type, old_locator, element_html)
            result["strategy"] = prediction.label
            result["confidence"] = prediction.confidence
        except Exception as e:
            result["error"] = f"ML prediction failed: {e}"
            result["heal_time_ms"] = round((time.time() - start) * 1000)
            self._log(idx, total, elr_file.name, result)
            return result

        # Step 4: Router check
        router_input = {
            "failure_context": {"action": action, "error_type": error_type},
            "dom_context": {"new_element_html": element_html},
        }
        router_decision = decide(router_input)
        if router_decision is not None:
            result["outcome"] = "NO_FIX"
            result["error"] = router_decision.get("reason", "Router rejected")
            result["heal_time_ms"] = round((time.time() - start) * 1000)
            self._log(idx, total, elr_file.name, result)
            return result

        # Step 5: Confidence gate
        if prediction.confidence < MIN_CONFIDENCE_CONSERVATIVE:
            result["outcome"] = "NO_FIX"
            result["error"] = f"Confidence too low ({prediction.confidence:.4f} < {MIN_CONFIDENCE_CONSERVATIVE})"
            result["heal_time_ms"] = round((time.time() - start) * 1000)
            self._log(idx, total, elr_file.name, result)
            return result

        # Step 6: Generate locators
        candidates = self.locator_gen.generate_candidates(element_html)
        best = self.locator_gen.pick_best(candidates)
        if not best:
            result["outcome"] = "NO_FIX"
            result["error"] = "No locator candidates generated"
            result["heal_time_ms"] = round((time.time() - start) * 1000)
            self._log(idx, total, elr_file.name, result)
            return result

        new_locator = best["value"]

        # Step 7: Patch
        output_dir = Path("data/scripts/healed/stress")
        output_dir.mkdir(parents=True, exist_ok=True)
        healed_path = output_dir / f"healed_{elr_file.stem}.py"

        patch_result = self.patcher.patch_locator(
            script_path=resolved_path,
            output_path=str(healed_path),
            failing_line=failing_line,
            old_locator=old_locator,
            new_locator=new_locator,
            action=action,
        )

        if patch_result.status != "SUCCESS":
            result["outcome"] = "FAILED"
            result["error"] = f"Patch failed: {patch_result.message}"
            result["heal_time_ms"] = round((time.time() - start) * 1000)
            self._log(idx, total, elr_file.name, result)
            return result

        result["patch_applied"] = True

        # Step 8: Validate syntax
        validation = HealingValidator.validate_script(patch_result.healed_script_path)
        if not validation["valid"]:
            result["outcome"] = "FAILED"
            result["error"] = f"Syntax validation failed: {validation['reason']}"
            result["heal_time_ms"] = round((time.time() - start) * 1000)
            self._log(idx, total, elr_file.name, result)
            return result

        # Success!
        result["outcome"] = "SUCCESS"
        result["heal_time_ms"] = round((time.time() - start) * 1000)
        result["new_locator"] = new_locator
        self._log(idx, total, elr_file.name, result)
        return result

    def _log(self, idx: int, total: int, name: str, result: dict):
        """Print progress line."""
        outcome = result["outcome"]
        strategy = result.get("strategy", "")
        confidence = result.get("confidence", 0.0)
        heal_time = result.get("heal_time_ms", 0)

        icons = {"SUCCESS": "OK", "NO_FIX": "--", "FAILED": "XX"}
        icon = icons.get(outcome, "??")

        line = f"  [{icon}] [{idx:3d}/{total}] {name:<45s} {outcome:<8s}"
        if strategy:
            line += f" | {strategy:<22s} | conf={confidence:.2f}"
        line += f" | {heal_time}ms"

        if self.verbose and result.get("error"):
            line += f"\n         > {result['error']}"

        print(line)


# ──────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="OmniiFix Stress Test")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed per-case output")
    parser.add_argument("--include-demo", action="store_true", help="Include demo test cases in addition to batch")
    args = parser.parse_args()

    print("=" * 70)
    print("OMINIFIX - STRESS TEST")
    print("=" * 70)

    input_dirs = ["data/synthetic_inputs/batch"]
    if args.include_demo:
        input_dirs.append("data/synthetic_inputs/demo")

    runner = StressTestRunner(verbose=args.verbose)
    output = runner.run(input_dirs)

    # Final verdict
    if output:
        rate = output.get("summary", {}).get("success_rate_pct", 0)
        if rate >= 70:
            print(f"\n[PASS] Healing success rate {rate}% >= 70% threshold")
        else:
            print(f"\n[WARN] Healing success rate {rate}% < 70% threshold")


if __name__ == "__main__":
    main()
