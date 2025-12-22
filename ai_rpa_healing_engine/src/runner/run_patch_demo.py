import json
from pathlib import Path

from src.locator_gen.locator_generator import LocatorGenerator
from src.patcher.libcst_patcher import ScriptPatcher
from src.engine.healing_validator import HealingValidator

from src.ml.dataset_logger import DatasetLogger

def main():
    dataset_logger = DatasetLogger()

    input_path = "data/synthetic_inputs/elr_input_search_01.json"
    inp = json.loads(Path(input_path).read_text(encoding="utf-8"))

    bot_id = inp["metadata"]["bot_id"]
    script_path = inp["failure_context"]["script_path"]
    failing_line = int(inp["failure_context"]["failing_line"])
    old_locator = inp["failure_context"]["old_locator"]
    element_html = inp["dom_context"]["new_element_html"]

    print(f"[INFO] bot_id={bot_id}")
    print(f"[INFO] script_path={script_path}")
    print(f"[INFO] failing_line={failing_line}")
    print(f"[INFO] old_locator={old_locator}")
    print(f"[INFO] element_html={element_html}")

    # 1) Generate RAW new locator candidates (your healing logic)
    gen = LocatorGenerator()
    candidates = gen.generate_candidates(element_html)
    best = gen.pick_best(candidates)

    if not best:
        raise RuntimeError("No locator candidates generated.")

    new_locator_raw = best["value"]

    # HARD GUARDS: enforce RAW invariant (no outer quotes)
    if (new_locator_raw.startswith("'") and new_locator_raw.endswith("'")) or (
        new_locator_raw.startswith('"') and new_locator_raw.endswith('"')
    ):
        raise RuntimeError(f"Locator must be RAW (no outer quotes). Got: {new_locator_raw}")

    print(f"[INFO] best_candidate={best}")

    # 2) Patch script (writes valid Python code)
    healed_path = f"data/scripts/healed/{bot_id}_search_flow_healed.py"
    patcher = ScriptPatcher()
    result = patcher.patch_locator(
        script_path=script_path,
        output_path=healed_path,
        failing_line=failing_line,
        old_locator=old_locator,
        new_locator=new_locator_raw,
    )

    print("[PATCH RESULT]", result)

    # 3) Validate healed script
    validation = HealingValidator.validate_script(result.healed_script_path)
    print("[VALIDATION]", validation)

    dataset_logger.log(
        bot_id=bot_id,
        error_type=inp["failure_context"]["error_type"],
        old_locator=old_locator,
        new_locator=new_locator_raw,
        strategy="LOCATOR_REGEN_LIBCST",
        confidence=best.get("score", 0) / 100.0,
        outcome="SUCCESS",
        element_html=element_html,
    )

    if not validation["valid"]:
        raise RuntimeError(f"Healed script invalid: {validation['reason']}")

    # 4) Output JSON for Predictive Testing
    out = {
        "metadata": {
            "healing_id": "HEAL-LOCAL-001",
            "bot_id": bot_id,
            "source_component": "code_healing_engine",
            "target_component": "predictive_testing_engine",
        },
        "healing_summary": {
            "status": result.status,
            "strategy_used": "LOCATOR_REGEN_LIBCST",
            "old_locator": old_locator,
            "new_locator": new_locator_raw,
            "confidence": best.get("score", 0) / 100.0,
            "validation": validation
        },
        "script_output": {
            "original_script_path": script_path,
            "healed_script_path": result.healed_script_path,
        },
    }

    out_path = "data/synthetic_outputs/healing_output_search_01.json"
    Path("data/synthetic_outputs").mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"[INFO] Output JSON saved to: {out_path}")


if __name__ == "__main__":
    main()
