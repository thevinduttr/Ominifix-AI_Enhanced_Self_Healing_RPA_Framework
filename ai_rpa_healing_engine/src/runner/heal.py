"""
Healing Engine Runner

Main entry point for the Code Healing Engine.
Processes ELR (Element Locator Report) JSON inputs and generates healed scripts.

Confidence-Aware Healing:
  - >= 0.70: Aggressive healing (use best candidate)
  - >= 0.50: Conservative healing (ID-based only)
  - <  0.50: NO_FIX (confidence too low)
"""

import json
import argparse
import logging
from pathlib import Path

from src.utils.path_manager import PathManager
from src.utils.script_path_resolver import resolve_script_path
from src.engine.healing_router import decide, base_output
from src.ml.strategy_predictor import StrategyPredictor
from src.locator_gen.locator_generator import LocatorGenerator
from src.patcher.libcst_patcher import ScriptPatcher
from src.engine.healing_validator import HealingValidator

logger = logging.getLogger(__name__)


MODEL_PATH = "models/strategy_selector_v1.pkl"

# Confidence thresholds (from strategy_schema.json)
MIN_CONFIDENCE_AGGRESSIVE = 0.70   # Use any best candidate
MIN_CONFIDENCE_CONSERVATIVE = 0.50  # ID-based only
# Below 0.50 = NO_FIX


def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(p: Path, data: dict):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def heal_from_dict(inp: dict, *, persist: bool = True) -> dict:
    """
    Core healing logic — takes an ELR dict and returns the healing output dict.

    Args:
        inp: ELR input dictionary.
        persist: If True, save output JSON and healed script to disk.
                 Set False for pure API / in-memory usage.

    Returns:
        Full healing output dictionary.
    """
    md = inp.get("metadata", {})
    fc = inp.get("failure_context", {})
    dom = inp.get("dom_context", {})

    bot_id = md.get("bot_id", "UNKNOWN_BOT")
    pm = PathManager(bot_id)

    output_json_path = pm.healing_output_path()
    healed_script_path = pm.healed_script_path()

    out = base_output(inp)

    # Resolve original script path using input + RPA_ROOT
    script_path_in = fc.get("script_path", "")
    resolved_script = resolve_script_path(script_path_in)

    # Model prediction (always for traceability)
    predictor = StrategyPredictor(MODEL_PATH)
    pred = predictor.predict(
        fc.get("error_type", ""),
        fc.get("old_locator", ""),
        dom.get("new_element_html", "")
    )
    out["model_info"]["confidence"] = float(pred.confidence)
    out["healing_summary"]["strategy_used"] = pred.label

    if not resolved_script.exists():
        out["healing_summary"]["status"] = "NO_FIX"
        out["healing_summary"]["strategy_used"] = "NO_FIX"
        out["healing_summary"]["validation"] = {
            "valid": True,
            "reason": (
                f"Original script not found. input script_path='{script_path_in}'. "
                f"resolved='{resolved_script}'. Set env var RPA_ROOT to RPA repo root."
            )
        }
        out["script_output"]["original_script_path"] = str(resolved_script)
        out["script_output"]["healed_script_path"] = ""
        if persist:
            save_json(output_json_path, out)
        return out

    decision = decide(inp)
    if decision:
        out["healing_summary"]["status"] = "NO_FIX"
        out["healing_summary"]["strategy_used"] = "NO_FIX"
        out["healing_summary"]["validation"] = {"valid": True, "reason": decision.reason}
        out["script_output"]["original_script_path"] = str(resolved_script)
        out["script_output"]["healed_script_path"] = ""
        if persist:
            save_json(output_json_path, out)
        return out

    # Generate locator candidates from DOM
    lg = LocatorGenerator()
    candidates = lg.generate_candidates(dom.get("new_element_html", ""))

    # Merge upstream element_candidate if provided (from Element Locator Engine)
    element_candidate = inp.get("element_candidate")
    if element_candidate:
        candidates = lg.merge_external_candidate(candidates, element_candidate)

    best = lg.pick_best(candidates)

    if not best:
        out["healing_summary"]["status"] = "NO_FIX"
        out["healing_summary"]["strategy_used"] = "NO_FIX"
        out["healing_summary"]["validation"] = {"valid": True, "reason": "No locator candidates generated."}
        out["script_output"]["original_script_path"] = str(resolved_script)
        out["script_output"]["healed_script_path"] = ""
        if persist:
            save_json(output_json_path, out)
        return out

    # ========================================
    # CONFIDENCE-AWARE HEALING GATE
    # ========================================
    # Strategy: balance automation with safety based on ML confidence
    
    if pred.confidence >= MIN_CONFIDENCE_AGGRESSIVE:
        # High confidence: use best candidate (aggressive healing)
        selected_locator = best.get("value", "")
        healing_mode = "aggressive"
    
    elif pred.confidence >= MIN_CONFIDENCE_CONSERVATIVE:
        # Medium confidence: only use ID-based locators (conservative healing)
        healing_mode = "conservative"
        
        # Check if best candidate is ID-based
        best_value = best.get("value", "")
        if best_value.startswith("#") or (best.get("type") == "css" and "#" in best_value.split("[", 1)[0]):
            # Safe: ID-based selector
            selected_locator = best_value
        else:
            # Unsafe: reject non-ID selectors in conservative mode
            out["healing_summary"]["status"] = "NO_FIX"
            out["healing_summary"]["strategy_used"] = "NO_FIX"
            out["healing_summary"]["old_locator"] = fc.get("old_locator", "")
            out["healing_summary"]["new_locator"] = ""
            out["healing_summary"]["confidence"] = float(pred.confidence)
            out["healing_summary"]["validation"] = {
                "valid": True,
                "reason": (
                    f"Conservative mode: ML confidence {pred.confidence:.4f} < {MIN_CONFIDENCE_AGGRESSIVE:.2f}. "
                    f"Best candidate '{best_value}' is not ID-based. Rejecting to prevent incorrect healing."
                )
            }
            out["script_output"]["original_script_path"] = str(resolved_script)
            out["script_output"]["healed_script_path"] = ""
            if persist:
                save_json(output_json_path, out)
            return out
    
    else:
        # Low confidence: reject healing (NO_FIX)
        out["healing_summary"]["status"] = "NO_FIX"
        out["healing_summary"]["strategy_used"] = "NO_FIX"
        out["healing_summary"]["old_locator"] = fc.get("old_locator", "")
        out["healing_summary"]["new_locator"] = ""
        out["healing_summary"]["confidence"] = float(pred.confidence)
        out["healing_summary"]["validation"] = {
            "valid": True,
            "reason": (
                f"ML confidence {pred.confidence:.4f} < {MIN_CONFIDENCE_CONSERVATIVE:.2f}. "
                f"Threshold too low for safe healing. Predicted strategy: {pred.label}"
            )
        }
        out["script_output"]["original_script_path"] = str(resolved_script)
        out["script_output"]["healed_script_path"] = ""
        if persist:
            save_json(output_json_path, out)
        return out

    # Patch script
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
        out["healing_summary"]["status"] = "FAILED"
        out["healing_summary"]["old_locator"] = fc.get("old_locator", "")
        out["healing_summary"]["new_locator"] = selected_locator
        out["healing_summary"]["confidence"] = best.get("score", 0) / 100.0
        out["healing_summary"]["patcher"] = "LibCST"
        out["healing_summary"]["validation"] = {"valid": False, "reason": patch_result.message}
        out["script_output"]["original_script_path"] = str(resolved_script)
        out["script_output"]["healed_script_path"] = ""
        out["model_info"]["healing_mode"] = healing_mode
        if persist:
            save_json(output_json_path, out)
        return out

    # Validate healed script
    validator = HealingValidator()
    validation = validator.validate_script(str(healed_script_path))
    status = "SUCCESS" if validation.get("valid") else "FAILED"

    out["healing_summary"]["status"] = status
    out["healing_summary"]["old_locator"] = fc.get("old_locator", "")
    out["healing_summary"]["new_locator"] = selected_locator
    out["healing_summary"]["confidence"] = best.get("score", 0) / 100.0
    out["healing_summary"]["patcher"] = "LibCST"
    out["healing_summary"]["validation"] = validation

    out["script_output"]["original_script_path"] = str(resolved_script)
    out["script_output"]["healed_script_path"] = str(healed_script_path)
    
    out["model_info"]["healing_mode"] = healing_mode
    out["model_info"]["ml_confidence"] = float(pred.confidence)

    if persist:
        save_json(output_json_path, out)
    return out


def heal_one(input_path: Path) -> str:
    """File-based wrapper: reads JSON from disk, heals, saves output, returns status string."""
    inp = load_json(input_path)
    out = heal_from_dict(inp, persist=True)
    return out["healing_summary"]["status"]


def process_inbox(inbox: Path):
    results = {"SUCCESS": 0, "FAILED": 0, "NO_FIX": 0}
    for f in inbox.rglob("*.json"):
        status = heal_one(f)
        results[status] += 1

    report = {"processed": sum(results.values()), "results": results}
    report_path = PathManager.run_report_path()
    save_json(report_path, report)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", help="Single ELR input JSON")
    ap.add_argument("--inbox", help="Inbox root folder")
    args = ap.parse_args()

    if args.input:
        logger.info("%s", heal_one(Path(args.input)))
    elif args.inbox:
        process_inbox(Path(args.inbox))
        logger.info("DONE")
    else:
        logger.info("Use --input <file> or --inbox <folder>")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
