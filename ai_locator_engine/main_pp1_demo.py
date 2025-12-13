import json
from orchestrator_sim.simulate_failure import run_bot_and_capture_failure
from locator_engine.fallback_logic import run_locator_engine

if __name__ == "__main__":
    print("=== STEP 1: Simulating bot failure (Orchestrator) ===")
    failure_ctx = run_bot_and_capture_failure()

    print("\n=== STEP 2: Running AI-Powered Element Locator Engine ===")
    report = run_locator_engine(failure_ctx)

    print("\n=== FINAL REPORT (for Code Healing Engine) ===")
    print(json.dumps(report, indent=2))
