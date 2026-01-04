import json
import argparse
from pathlib import Path

from src.utils.path_manager import PathManager
from src.utils.script_path_resolver import resolve_script_path
from src.engine.healing_router import decide, base_output
from src.ml.strategy_predictor import StrategyPredictor
from src.locator_gen.locator_generator import LocatorGenerator
from src.patcher.libcst_patcher import ScriptPatcher
from src.engine.healing_validator import HealingValidator


MODEL_PATH = "models/strategy_selector_v1.pkl"


def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(p: Path, data: dict):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def heal_one(input_path: Path) -> str:
    inp = load_json(input_path)

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
        save_json(output_json_path, out)
        return "NO_FIX"

    decision = decide(inp)
    if decision:
        out["healing_summary"]["status"] = "NO_FIX"
        out["healing_summary"]["strategy_used"] = "NO_FIX"
        out["healing_summary"]["validation"] = {"valid": True, "reason": decision.reason}
        out["script_output"]["original_script_path"] = str(resolved_script)
        out["script_output"]["healed_script_path"] = ""
        save_json(output_json_path, out)
        return "NO_FIX"

    # Generate best locator candidate from DOM
    lg = LocatorGenerator()
    candidates = lg.generate_candidates(dom.get("new_element_html", ""))
    best = lg.pick_best(candidates)

    if not best:
        out["healing_summary"]["status"] = "NO_FIX"
        out["healing_summary"]["strategy_used"] = "NO_FIX"
        out["healing_summary"]["validation"] = {"valid": True, "reason": "No locator candidates generated."}
        out["script_output"]["original_script_path"] = str(resolved_script)
        out["script_output"]["healed_script_path"] = ""
        save_json(output_json_path, out)
        return "NO_FIX"

    # Patch script
    patcher = ScriptPatcher()
    patch_result = patcher.patch_locator(
        script_path=str(resolved_script),
        output_path=str(healed_script_path),
        failing_line=int(fc.get("failing_line", 0)),
        old_locator=fc.get("old_locator", ""),
        new_locator=best.get("value", ""),
        action=(fc.get("action") or "").strip().lower(),
    )

    if patch_result.status != "SUCCESS":
        out["healing_summary"]["status"] = "FAILED"
        out["healing_summary"]["old_locator"] = fc.get("old_locator", "")
        out["healing_summary"]["new_locator"] = best.get("value", "")
        out["healing_summary"]["confidence"] = best.get("score", 0) / 100.0
        out["healing_summary"]["patcher"] = "LibCST"
        out["healing_summary"]["validation"] = {"valid": False, "reason": patch_result.message}
        out["script_output"]["original_script_path"] = str(resolved_script)
        out["script_output"]["healed_script_path"] = ""
        save_json(output_json_path, out)
        return "FAILED"

    # Validate healed script
    validator = HealingValidator()
    validation = validator.validate_script(str(healed_script_path))
    status = "SUCCESS" if validation.get("valid") else "FAILED"

    out["healing_summary"]["status"] = status
    out["healing_summary"]["old_locator"] = fc.get("old_locator", "")
    out["healing_summary"]["new_locator"] = best.get("value", "")
    out["healing_summary"]["confidence"] = best.get("score", 0) / 100.0
    out["healing_summary"]["patcher"] = "LibCST"
    out["healing_summary"]["validation"] = validation

    out["script_output"]["original_script_path"] = str(resolved_script)
    out["script_output"]["healed_script_path"] = str(healed_script_path)

    save_json(output_json_path, out)
    return status


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
        print(heal_one(Path(args.input)))
    elif args.inbox:
        process_inbox(Path(args.inbox))
        print("DONE")
    else:
        print("Use --input <file> or --inbox <folder>")


if __name__ == "__main__":
    main()
