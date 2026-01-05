import json
from pathlib import Path

from src.locator_gen.locator_generator import LocatorGenerator
from src.patcher.libcst_patcher import ScriptPatcher
from src.engine.healing_validator import HealingValidator
from src.ml.dataset_logger import DatasetLogger
from src.ml.strategy_predictor import StrategyPredictor


def main():
    # ---------- INPUT ----------
    input_path = "data/synthetic_inputs/elr_input_search_01.json"
    inp = json.loads(Path(input_path).read_text(encoding="utf-8"))

    bot_id = inp["metadata"]["bot_id"]
    script_path = inp["failure_context"]["script_path"]
    failing_line = int(inp["failure_context"]["failing_line"])
    old_locator = inp["failure_context"]["old_locator"]
    error_type = inp["failure_context"]["error_type"]
    element_html = inp["dom_context"]["new_element_html"]

    print(f"[INFO] bot_id={bot_id}")
    print(f"[INFO] script_path={script_path}")
    print(f"[INFO] failing_line={failing_line}")
    print(f"[INFO] error_type={error_type}")
    print(f"[INFO] old_locator={old_locator}")
    print(f"[INFO] element_html={element_html}")

    # ---------- INIT COMPONENTS ----------
    locator_gen = LocatorGenerator()
    patcher = ScriptPatcher()
    validator = HealingValidator()
    dataset_logger = DatasetLogger()

    # ML predictor (Kaggle trained)
    predictor = StrategyPredictor("models/strategy_selector_v1.pkl")

    # ---------- MODEL PREDICTION ----------
    prediction = predictor.predict(
        error_type=error_type,
        old_locator=old_locator,
        element_html=element_html
    )
    print(f"[MODEL] predicted_strategy={prediction.label} confidence={prediction.confidence:.4f}")

    # ---------- LOCATOR GENERATION ----------
    candidates = locator_gen.generate_candidates(element_html)
    best = locator_gen.pick_best(candidates)

    if not best:
        print("[ERROR] No locator candidates generated. Cannot heal.")
        # Log dataset as failure
        dataset_logger.log(
            bot_id=bot_id,
            error_type=error_type,
            old_locator=old_locator,
            new_locator="",
            strategy="NO_FIX",
            confidence=0.0,
            outcome="FAILED",
            element_html=element_html,
        )
        return

    new_locator_raw = best["value"]
    confidence = best.get("score", 0) / 100.0
    print(f"[INFO] best_candidate={best}")

    # ---------- PATCH SCRIPT ----------
    healed_path = f"data/scripts/healed/{bot_id}_search_flow_healed.py"
    result = patcher.patch_locator(
        script_path=script_path,
        output_path=healed_path,
        failing_line=failing_line,
        old_locator=old_locator,
        new_locator=new_locator_raw,
    )
    print("[PATCH RESULT]", result)

    if result.status != "SUCCESS":
        dataset_logger.log(
            bot_id=bot_id,
            error_type=error_type,
            old_locator=old_locator,
            new_locator=new_locator_raw,
            strategy="NO_FIX",
            confidence=confidence,
            outcome="FAILED",
            element_html=element_html,
        )
        print("[ERROR] Patch failed. Dataset logged as FAILED.")
        return

    # ---------- VALIDATE HEALED SCRIPT ----------
    validation = validator.validate_script(result.healed_script_path)
    print("[VALIDATION]", validation)

    if not validation["valid"]:
        dataset_logger.log(
            bot_id=bot_id,
            error_type=error_type,
            old_locator=old_locator,
            new_locator=new_locator_raw,
            strategy="NO_FIX",
            confidence=confidence,
            outcome="FAILED",
            element_html=element_html,
        )
        print("[ERROR] Healed script invalid. Dataset logged as FAILED.")
        return

    # ---------- LOG DATASET (SUCCESS) ----------
    # Use ML predicted label (so your dataset contains model-driven decisions)
    dataset_logger.log(
        bot_id=bot_id,
        error_type=error_type,
        old_locator=old_locator,
        new_locator=new_locator_raw,
        strategy=prediction.label,
        confidence=prediction.confidence,
        outcome="SUCCESS",
        element_html=element_html,
    )

    # ---------- OUTPUT JSON (Predictive Testing Ready) ----------
    out = {
        "metadata": {
            "healing_id": "HEAL-LOCAL-ML-001",
            "bot_id": bot_id,
            "source_component": "code_healing_engine",
            "target_component": "predictive_testing_engine",
        },
        "healing_summary": {
            "status": "SUCCESS",
            "strategy_used": prediction.label,
            "old_locator": old_locator,
            "new_locator": new_locator_raw,
            "confidence": confidence,
            "validation": validation
        },
        "script_output": {
            "original_script_path": script_path,
            "healed_script_path": result.healed_script_path
        },
        "model_info": {
            "model_used": "strategy_selector_v1",
            "model_source": "kaggle",
            "predicted_strategy": prediction.label,
            "model_confidence": prediction.confidence
        }
    }

    out_path = "data/synthetic_outputs/healing_output_search_01.json"
    Path("data/synthetic_outputs").mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(f"[INFO] Output JSON saved to: {out_path}")
    print("[DONE] Healing pipeline completed successfully.")


if __name__ == "__main__":
    main()
