import json
from pathlib import Path

from src.locator_gen.locator_generator import LocatorGenerator
from src.patcher.script_patcher import ScriptPatcher


def main():
    input_path = "data/synthetic_inputs/elr_input_search_01.json"
    inp = json.loads(Path(input_path).read_text(encoding="utf-8"))

    bot_id = inp["metadata"]["bot_id"]
    script_path = inp["failure_context"]["script_path"]
    failing_line = int(inp["failure_context"]["failing_line"])
    old_locator = inp["failure_context"]["old_locator"]
    element_html = inp["dom_context"]["new_element_html"]

    # 1) Generate new locator (your healing work)
    gen = LocatorGenerator()
    candidates = gen.generate_candidates(element_html)
    best = gen.pick_best(candidates)
    if not best:
        print("No locator candidates generated. Cannot heal.")
        return

    new_locator = best["value"]

    # 2) Patch the script
    healed_path = f"data/scripts/healed/{bot_id}_search_flow_healed.py"
    patcher = ScriptPatcher()
    result = patcher.patch_locator(
        script_path=script_path,
        output_path=healed_path,
        failing_line=failing_line,
        old_locator=old_locator,
        new_locator=new_locator,
    )

    print("PATCH RESULT:", result)

    # 3) Create output JSON for Predictive Testing
    out = {
        "metadata": {
            "healing_id": "HEAL-LOCAL-001",
            "bot_id": bot_id,
            "source_component": "code_healing_engine",
            "target_component": "predictive_testing_engine"
        },
        "healing_summary": {
            "status": result.status,
            "strategy_used": "LOCATOR_REGEN_V1",
            "old_locator": old_locator,
            "new_locator": new_locator,
            "confidence": best.get("score", 0) / 100.0
        },
        "script_output": {
            "original_script_path": script_path,
            "healed_script_path": result.healed_script_path
        }
    }

    out_path = "data/synthetic_outputs/healing_output_search_01.json"
    Path("data/synthetic_outputs").mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Output JSON saved to: {out_path}")


if __name__ == "__main__":
    main()
