import sys; sys.path.insert(0, '.')
from app.adapters.healing_input_adapter import HealingInputAdapter
from pathlib import Path
import json

adapter = HealingInputAdapter()

real_friend_payload = {
  "metadata": {
    "healing_id": "HEAL-a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "report_id": "ELR-E2E-001",
    "run_id": "e2e-test-20260305-001",
    "bot_id": "BOT-ECOMMERCE-01",
    "timestamp": "2026-03-05T14:00:05.123456",
    "source_component": "code_healing_engine",
    "target_component": "predictive_testing_engine"
  },
  "failure_context": {
    "script_path": "data/scripts/broken/e2e/bot1_ecommerce_checkout.py",
    "failing_line": 15,
    "action": "click",
    "old_locator": "#submit-order-old",
    "error_type": "ELEMENT_NOT_FOUND",
    "error_message": "Timeout 30000ms exceeded waiting for selector '#submit-order-old'"
  },
  "element_candidate": {
    "css": "#submit-order",
    "xpath": "//button[@id='submit-order']",
    "score": 85,
    "strategy": "attribute_match"
  },
  "healing_summary": {
    "status": "SUCCESS",
    "strategy_used": "LOCATOR_REGEN_LIBCST",
    "action": "click",
    "old_locator": "#submit-order-old",
    "new_locator": "#submit-order",
    "confidence": 0.85
  },
  "script_output": {
    "original_script_path": "data/scripts/broken/e2e/bot1_ecommerce_checkout.py",
    "healed_script_path": "data/scripts/healed/BOT-ECOMMERCE-01/2026-03-05/bot1_ecommerce_checkout_healed.py"
  },
  "model_info": {"model": "strategy_selector_v1", "confidence": 0.85}
}

result = adapter.adapt(real_friend_payload)
print("=== Adapter Output ===")
print(json.dumps(result, indent=2))
print()
print("script paths resolved to:")
print("  original:", result["script_output"]["original_script_path"])
print("  healed  :", result["script_output"]["healed_script_path"])
print("  original exists?", Path(result["script_output"]["original_script_path"]).exists())
print("  healed exists?  ", Path(result["script_output"]["healed_script_path"]).exists())
