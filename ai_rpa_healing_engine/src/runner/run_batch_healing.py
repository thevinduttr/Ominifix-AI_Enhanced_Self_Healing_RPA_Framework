import json
import logging
from pathlib import Path

from src.locator_gen.locator_generator import LocatorGenerator
from src.patcher.libcst_patcher import ScriptPatcher
from src.engine.healing_validator import HealingValidator
from src.ml.dataset_logger import DatasetLogger
from src.ml.sample_generator import SampleGenerator

logger = logging.getLogger(__name__)


def label_strategy(best_locator: dict, action: str, element_html: str) -> str:
    """
    Intelligent strategy labeling based on locator characteristics and action type.
    
    5-class taxonomy:
      - LOCATOR_REGEN_LIBCST: ID-based selectors (#id)
      - FALLBACK_LOCATOR: Attribute-based (aria-label, placeholder, name, type)
      - FALLBACK_XPATH: XPath-based (no CSS-friendly attributes)
      - CLICK_ONLY: Button/link click actions
      - NO_FIX: Empty/invalid input
    """
    locator_value = best_locator.get("value", "")
    locator_type = best_locator.get("type", "css")
    
    # Check for click-specific actions on buttons/links
    if action == "click":
        # Check if element is button or link
        if any(tag in element_html.lower() for tag in ["<button", "<a ", "role=\"button\""]):
            # If it has an ID, it's still CLICK_ONLY
            if locator_value.startswith("#") or locator_type == "css" and "#" in locator_value:
                return "CLICK_ONLY"
            return "CLICK_ONLY"
    
    # ID-based is highest confidence
    if locator_value.startswith("#"):
        return "LOCATOR_REGEN_LIBCST"
    
    # Check if it's an ID-based CSS selector (e.g., "button#submitBtn")
    if locator_type == "css" and "#" in locator_value.split("[", 1)[0]:
        return "LOCATOR_REGEN_LIBCST"
    
    # XPath fallback
    if locator_type == "xpath":
        return "FALLBACK_XPATH"
    
    # Attribute-based CSS selectors (aria-label, placeholder, name, etc.)
    if locator_type == "css" and any(attr in locator_value for attr in ["[aria-label=", "[placeholder=", "[name=", "[type="]):
        return "FALLBACK_LOCATOR"
    
    # Default fallback
    return "FALLBACK_LOCATOR"


def main():
    # Generate more samples (150 gives better balance and statistical significance)
    gen = SampleGenerator()
    count = gen.generate(n=150)
    logger.info("Generated %d synthetic inputs", count)

    locator_gen = LocatorGenerator()
    patcher = ScriptPatcher()
    dataset_logger = DatasetLogger()

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
        action = inp["failure_context"].get("action", "fill")
        old_locator = inp["failure_context"]["old_locator"]
        element_html = inp["dom_context"]["new_element_html"]

        # 1) Generate locator
        candidates = locator_gen.generate_candidates(element_html)
        best = locator_gen.pick_best(candidates)

        if not best:
            failed += 1
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
            continue

        new_locator = best["value"]
        confidence = best.get("score", 0) / 100.0
        strategy = label_strategy(best, action, element_html)

        # 2) Patch
        healed_path = healed_dir / f"{bot_id}_healed.py"
        result = patcher.patch_locator(
            script_path=script_path,
            output_path=str(healed_path),
            failing_line=failing_line,
            old_locator=old_locator,
            new_locator=new_locator,
            action=action,
        )

        if result.status != "SUCCESS":
            failed += 1
            dataset_logger.log(
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
            dataset_logger.log(
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
        dataset_logger.log(
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

    logger.info("SUCCESS=%d FAILED=%d", success, failed)
    logger.info("Dataset updated at: data/ml/healing_dataset.csv")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
