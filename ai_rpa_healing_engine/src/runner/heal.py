import json
import argparse
from pathlib import Path

from src.utils.path_manager import PathManager
from src.engine.healing_router import decide, base_output
from src.ml.strategy_predictor import StrategyPredictor
from src.locator_gen.locator_generator import LocatorGenerator
from src.patcher.libcst_patcher import ScriptPatcher
from src.engine.healing_validator import HealingValidator


MODEL_PATH = "models/strategy_selector_v1.pkl"


def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(p: Path, data: dict):
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def heal_one(input_path: Path) -> str:
    inp = load_json(input_path)
    bot_id = inp["metadata"]["bot_id"]

    pm = PathManager(bot_id)
    output_json_path = pm.healing_output_path()
    healed_script_path = pm.healed_script_path()

    # ML strategy prediction (always)
    predictor = StrategyPredictor(MODEL_PATH)
    pred = predictor.predict(
        inp["failure_context"]["error_type"],
        inp["failure_context"].get("old_locator", ""),
        inp["dom_context"].get("new_element_html", "")
    )

    decision = decide(inp)
    out = base_output(inp)

    if decision:
        out["healing_summary"]["validation"]["reason"] = decision.reason
        out["model_info"] = {
            "model": "strategy_selector_v1",
            "confidence": pred.confidence
        }
        save_json(output_json_path, out)
        return "NO_FIX"

    # Locator generation
    lg = LocatorGenerator()
    candidates = lg.generate_candidates(inp["dom_context"]["new_element_html"])
    best = lg.pick_best(candidates)

    # Patch
    patcher = ScriptPatcher()
    fc = inp["failure_context"]

    patch_result = patcher.patch_locator(
        script_path=fc["script_path"],
        output_path=str(healed_script_path),
        failing_line=int(fc["failing_line"]),
        old_locator=fc["old_locator"],
        new_locator=best["value"],
        action=fc["action"]
    )

    # Validate
    validator = HealingValidator()
    validation = validator.validate_script(str(healed_script_path))

    out["healing_summary"].update({
        "status": "SUCCESS" if validation["valid"] else "FAILED",
        "strategy_used": pred.label,
        "new_locator": best["value"],
        "confidence": best["score"] / 100.0,
        "patcher": "LibCST"
    })

    out["healing_summary"]["validation"] = validation
    out["script_output"]["healed_script_path"] = str(healed_script_path)
    out["model_info"] = {
        "model": "strategy_selector_v1",
        "confidence": pred.confidence
    }

    save_json(output_json_path, out)
    return out["healing_summary"]["status"]


def process_inbox(inbox: Path):
    results = {"SUCCESS": 0, "FAILED": 0, "NO_FIX": 0}

    for f in inbox.rglob("*.json"):
        status = heal_one(f)
        results[status] += 1

    report = {
        "processed": sum(results.values()),
        "results": results
    }

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
    else:
        print("Use --input <file> or --inbox <folder>")


if __name__ == "__main__":
    main()
