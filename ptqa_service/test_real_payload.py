import sys, json, http.client

HOST = "127.0.0.1"
PORT = 8000

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
    "error_message": "Timeout 30000ms exceeded"
  },
  "dom_context": {
    "page_url": "https://example.com/checkout",
    "page_name": "Checkout Page",
    "new_element_html": "<button id=\"submit-order\" class=\"btn btn-primary\">Place Order</button>"
  },
  "element_expectation": {"expected_role": "button", "expected_text": "Place Order"},
  "element_candidate": {
    "css": "#submit-order",
    "xpath": "//button[@id='submit-order']",
    "full_xpath": "/html/body/div[2]/form/button[1]",
    "score": 85,
    "strategy": "attribute_match"
  },
  "healing_summary": {
    "status": "SUCCESS",
    "strategy_used": "LOCATOR_REGEN_LIBCST",
    "action": "click",
    "old_locator": "#submit-order-old",
    "new_locator": "#submit-order",
    "confidence": 0.85,
    "patcher": "libcst",
    "validation": {"valid": True, "reason": "OK"}
  },
  "script_output": {
    "original_script_path": "data/scripts/broken/e2e/bot1_ecommerce_checkout.py",
    "healed_script_path": "data/scripts/healed/BOT-ECOMMERCE-01/2026-03-05/bot1_ecommerce_checkout_healed.py"
  },
  "model_info": {"model": "strategy_selector_v1", "confidence": 0.85}
}

print("Sending REAL friend payload to server (bots running, ~15-20s)...")
body = json.dumps(real_friend_payload).encode()
conn = http.client.HTTPConnection(HOST, PORT, timeout=90)
conn.request("POST", "/ptqa/evaluate-healing", body=body,
             headers={"Content-Type": "application/json"})
resp = conn.getresponse()
raw  = resp.read()
conn.close()

if resp.status != 200:
    print(f"HTTP {resp.status} ERROR:")
    print(raw.decode()[:600])
    sys.exit(1)

d = json.loads(raw)
print()
print("=" * 50)
print("  REAL FRIEND PAYLOAD RESULT")
print("=" * 50)
print(f"  recommendation : {d['recommendation']}")
print(f"  confidence     : {round(d['confidence'], 3)}")
print(f"  risk_level     : {d['risk_level']}")
qm = d.get("quality_metrics", {})
print(f"  pass_before    : {qm.get('pass_rate_before')}")
print(f"  pass_after     : {qm.get('pass_rate_after')}")
print(f"  healing_effect : {qm.get('healing_effect')}")
print()
print("  reasons:")
for r in d.get("reasons", []):
    print(f"    - {r}")
