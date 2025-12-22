import json
from pathlib import Path

from src.locator_gen.locator_generator import LocatorGenerator
from src.patcher.libcst_patcher import ScriptPatcher
from src.engine.healing_validator import HealingValidator
from src.ml.dataset_logger import DatasetLogger
from src.ml.sample_generator import SampleGenerator


def label_strategy(best_locator: str) -> str:
    # If id-based, it's our "main" locator regen strategy
    if best_locator.startswith("#") or "#" in best_locator.split("[", 1)[0]:
        return "LOCATOR_REGEN_LIBCST"
    return "FALLBACK_LOCATOR"


def main():
    # Generate more samples (60 gives better balance)
    gen = SampleGenerator()
    count = gen.generate(n=60)
    print(f"[INFO] Generated {count} synthetic inputs")

    locator_gen = LocatorGenerator()
    patcher = ScriptPatcher()
    logger = DatasetLogger()

    inputs_dir = Path("data/synthetic_inputs/batch")
    healed_dir = Path("data/scripts/healed/batch")
    healed_dir.mkdir(parents=True, exist_ok=True)

    success = 0
    failed = 0

    for json_file in sorted(inputs_dir.glob("elr_input_*.json")):
        inp = json.loads(json_file.read_text(encoding="utf-8"))

        bot_id = inp["metadata"]["bot_id"]
        error_type = inp["failure_context"]["error_type"]
        script_path = inp["failure_context"]["script_path"]
        failing_line = int(inp["failure_context"]["failing_line"])
        old_locator = inp["failure_context"]["old_locator"]
        element_html = inp["dom_context"]["new_element_html"]

        # 1) Generate locator
        candidates = locator_gen.generate_candidates(element_html)
        best = locator_gen.pick_best(candidates)

        if not best:
            failed += 1
            logger.log(
                bot_id=bot_id,
                error_type=error_type,
                old_locator=old_locator,
                new_locator="",
                strategy="NO_FIX",
                confidence=0.0,
                outcome="FAILED",
                element_html=element_html,
            )
            continue

        new_locator = best["value"]
        confidence = best.get("score", 0) / 100.0
        strategy = label_strategy(new_locator)

        # 2) Patch
        healed_path = healed_dir / f"{bot_id}_healed.py"
        result = patcher.patch_locator(
            script_path=script_path,
            output_path=str(healed_path),
            failing_line=failing_line,
            old_locator=old_locator,
            new_locator=new_locator,
        )

        if result.status != "SUCCESS":
            failed += 1
            logger.log(
                bot_id=bot_id,
                error_type=error_type,
                old_locator=old_locator,
                new_locator=new_locator,
                strategy="NO_FIX",
                confidence=confidence,
                outcome="FAILED",
                element_html=element_html,
            )
            continue

        # 3) Validate syntax
        validation = HealingValidator.validate_script(result.healed_script_path)
        if not validation["valid"]:
            failed += 1
            logger.log(
                bot_id=bot_id,
                error_type=error_type,
                old_locator=old_locator,
                new_locator=new_locator,
                strategy="NO_FIX",
                confidence=confidence,
                outcome="FAILED",
                element_html=element_html,
            )
            continue

        # 4) Log as success with strategy label
        logger.log(
            bot_id=bot_id,
            error_type=error_type,
            old_locator=old_locator,
            new_locator=new_locator,
            strategy=strategy,
            confidence=confidence,
            outcome="SUCCESS",
            element_html=element_html,
        )
        success += 1

    print(f"[RESULT] SUCCESS={success} FAILED={failed}")
    print("[INFO] Dataset updated at: data/ml/healing_dataset.csv")


if __name__ == "__main__":
    main()
