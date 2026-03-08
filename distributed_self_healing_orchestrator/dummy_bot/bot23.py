import requests
import time
import random
import os

# Bot23: send a few heartbeats, then report a structured failure payload
MONITOR_URL = os.environ.get('MONITOR_URL', 'http://localhost:8000/heartbeat')
BOT_ID = os.environ.get('BOT_ID', 'BOT-23')
HEARTBEATS = int(os.environ.get('HEARTBEATS', '5'))
INTERVAL = float(os.environ.get('INTERVAL', '4'))

print(f'Bot23 sending heartbeats to {MONITOR_URL}. Will fail after {HEARTBEATS} heartbeats.')

count = 0
while True:
    if count < HEARTBEATS:
        try:
            requests.post(MONITOR_URL, json={"botId": BOT_ID, "meta": {"instance": "bot23"}}, timeout=2)
            print(f'Heartbeat {count + 1}/{HEARTBEATS} sent from {BOT_ID}')
        except Exception as e:
            print('Heartbeat error (bot23):', e)
        count += 1
        time.sleep(INTERVAL)
        continue

    failure_payload = {
        "botId": BOT_ID,
        "page_url": "https://dummy.local/api/payments",
        "failure_type": "NETWORK_ERROR",
        "failed_action": "request",
        "element_role": "api_call",
        "expected_text": "HTTP 200",
        "old_locator": "https://dummy.local/api/payments",
        "old_locator_type": "url",
        "error_message": "Connection timed out while calling upstream service",
        "page_html": "",
        "screenshot_path": "",
        "metadata": {
            "bot_id": "RPA-0020",
            "workflow_step": "submit_payment",
            "run_id": "RUN-PP1-NETWORK-TIMEOUT",
            "error_type": "NETWORK_ERROR"
        }
    }

    try:
        report_failure_url = MONITOR_URL.replace('/heartbeat', '/report_failure')
        requests.post(report_failure_url, json=failure_payload, timeout=3)
        print('Failure payload sent from bot23:')
        print(failure_payload)
    except Exception as e:
        print('Failed to send failure payload (bot23):', e)

    print(f'{BOT_ID} simulated failure and stopped heartbeats.')
    break
