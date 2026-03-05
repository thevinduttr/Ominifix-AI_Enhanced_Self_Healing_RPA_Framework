"""
Live API test — proves both payload formats work against the running server.
Run from ptqa_service/ directory.
"""
import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"

# ─── payloads ────────────────────────────────────────────────────────────────

YOUR_FORMAT = {
    "metadata": {
        "healing_id": "H_STABLE_001",
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
        "healing_id":       "HEAL-a1b2c3d4",
        "bot_id":           "BOT_ADD_REMOVE",          # <-- friend uses bot_id
        "source_component": "code_healing_engine",      # <-- triggers adapter
        "run_id":           "RUN-xyz",
        "report_id":        "RPT-001"
    },
    "failure_context": {
        "error_type": "ELEMENT_NOT_FOUND"               # <-- infers last_n_failures=3
    },
    "healing_summary": {
        "status":       "SUCCESS",                      # <-- uppercase
        "strategy_used": "LOCATOR_REGEN_LIBCST",        # <-- verbose name
        "old_locator":  "#add-element-old",
        "new_locator":  "#add-element",
        "confidence":   0.88                            # <-- friend's field name
    },
    "script_output": {
        "original_script_path": "bots/demo_add_remove_original.py",
        "healed_script_path":   "bots/demo_add_remove.py"
    },
    "model_info": {
        "model": "strategy_selector_v1",
        "confidence": 0.88
    }
}

# ─── helper ──────────────────────────────────────────────────────────────────

def post(payload, label):
    print(f"\n{'='*55}")
    print(f"  {label}")
    print(f"{'='*55}")
    body = json.dumps(payload).encode()
    req  = urllib.request.Request(
        f"{BASE}/ptqa/evaluate-healing",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            d = json.loads(resp.read())
        print(f"  recommendation : {d['recommendation']}")
        print(f"  confidence     : {round(d['confidence'], 3)}")
        print(f"  risk_level     : {d['risk_level']}")
        qm = d.get("quality_metrics", {})
        print(f"  pass_before    : {qm.get('pass_rate_before', 'n/a')}")
        print(f"  pass_after     : {qm.get('pass_rate_after',  'n/a')}")
        reasoning = d.get("reasoning") or d.get("reasoning_summary", "")
        if reasoning:
            print(f"  reasoning      : {str(reasoning)[:120]}")
    except urllib.error.HTTPError as e:
        print(f"  HTTP ERROR {e.code}: {e.read().decode()[:400]}")
    except Exception as ex:
        print(f"  ERROR: {ex}")

# ─── run ─────────────────────────────────────────────────────────────────────

print("\n🚀  PTQA Live API Tests — both payload formats")
print("   (each call runs real Playwright bots, ~15-20 s per test)")

post(YOUR_FORMAT,   "TEST A — YOUR native PTQA format")
post(HEALINGCOMPONENT_FORMAT,"TEST B — FRIEND'S Code Healing Engine format  (adapter converts it)")

print("\n✅  Done")
