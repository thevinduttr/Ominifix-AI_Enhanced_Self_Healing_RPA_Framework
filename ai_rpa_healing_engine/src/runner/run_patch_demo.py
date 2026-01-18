import json
import logging
from pathlib import Path

from src.locator_gen.locator_generator import LocatorGenerator
from src.patcher.libcst_patcher import ScriptPatcher
from src.engine.healing_validator import HealingValidator
from src.ml.dataset_logger import DatasetLogger
from src.ml.strategy_predictor import StrategyPredictor

logger = logging.getLogger(__name__)


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

    logger.info("bot_id=%s", bot_id)
    logger.info("script_path=%s", script_path)
    logger.info("failing_line=%s", failing_line)
    logger.info("error_type=%s", error_type)
    logger.info("old_locator=%s", old_locator)
    logger.info("element_html=%s", element_html)

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
    logger.info("predicted_strategy=%s confidence=%.4f", prediction.label, prediction.confidence)

    # ---------- LOCATOR GENERATION ----------
    candidates = locator_gen.generate_candidates(element_html)
    best = locator_gen.pick_best(candidates)

    if not best:
        logger.error("No locator candidates generated. Cannot heal.")
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
    logger.info("best_candidate=%s", best)

    # ---------- PATCH SCRIPT ----------
    healed_path = f"data/scripts/healed/{bot_id}_search_flow_healed.py"
    result = patcher.patch_locator(
        script_path=script_path,
        output_path=healed_path,
        failing_line=failing_line,
        old_locator=old_locator,
        new_locator=new_locator_raw,
    )
    logger.info("PATCH RESULT: %s", result)

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
        logger.error("Patch failed. Dataset logged as FAILED.")
        return

    # ---------- VALIDATE HEALED SCRIPT ----------
    validation = validator.validate_script(result.healed_script_path)
    logger.info("VALIDATION: %s", validation)

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
        logger.error("Healed script invalid. Dataset logged as FAILED.")
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

    logger.info("Output JSON saved to: %s", out_path)
    logger.info("Healing pipeline completed successfully.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
