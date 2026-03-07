"""
Sends BOTH payload formats to the live PTQA server and saves results to /tmp/ptqa_results.json
"""
import json, http.client, sys

BASE_HOST = "127.0.0.1"
BASE_PORT = 8000

YOUR_FORMAT = {
    "metadata": {
        "healing_id": "H_STABLE_002",
        "script_id":  "BOT_ADD_REMOVE",
        "environment": "qa",
        "last_n_failures": 0,
        "headless": True
    },
    "healing_summary": {
        "status":       "success",
        "old_locator":  "text=Add Element",
        "new_locator":  "text=Add Element",
        "strategy_used": "dom"
    },
    "model_info": {"model_confidence": 0.85},
    "script_output": {
        "original_script_path": "bots/demo_add_remove_original.py",
        "healed_script_path":   "bots/demo_add_remove.py"
    }
}

HEALINGCOMPONENT_FORMAT = {
    "metadata": {
        "healing_id":       "HEAL-friend-001",
        "bot_id":           "BOT_ADD_REMOVE",
        "source_component": "code_healing_engine",
        "run_id":           "RUN-xyz",
        "report_id":        "RPT-001"
    },
    "failure_context": {"error_type": "ELEMENT_NOT_FOUND"},
    "healing_summary": {
        "status":       "SUCCESS",
        "strategy_used": "LOCATOR_REGEN_LIBCST",
        "old_locator":  "#add-element-old",
        "new_locator":  "#add-element",
        "confidence":   0.88
    },
    "script_output": {
        "original_script_path": "bots/demo_add_remove_original.py",
        "healed_script_path":   "bots/demo_add_remove.py"
    },
    "model_info": {"model": "strategy_selector_v1", "confidence": 0.88}
}

results = {}
for label, payload in [("TEST_A_YOUR_FORMAT", YOUR_FORMAT), ("TEST_B_HEALINGCOMPONENT_FORMAT", HEALINGCOMPONENT_FORMAT)]:
    sys.stderr.write(f"Sending {label} ...\n"); sys.stderr.flush()
    body = json.dumps(payload).encode()
    try:
        conn = http.client.HTTPConnection(BASE_HOST, BASE_PORT, timeout=90)
        conn.request("POST", "/ptqa/evaluate-healing", body=body,
                     headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        raw  = resp.read()
        conn.close()
        results[label] = json.loads(raw)
        sys.stderr.write(f"  OK — {results[label]['recommendation']}\n"); sys.stderr.flush()
    except Exception as e:
        results[label] = {"error": str(e)}
        sys.stderr.write(f"  FAIL — {e}\n"); sys.stderr.flush()

out = "/tmp/ptqa_results.json"
with open(out, "w") as f:
    json.dump(results, f, indent=2)
sys.stderr.write(f"\nResults saved to {out}\n")
