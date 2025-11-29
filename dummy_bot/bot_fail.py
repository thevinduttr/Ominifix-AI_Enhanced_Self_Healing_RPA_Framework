import requests
import time
import random
import os

# Controlled failure bot: send N heartbeats then stop to simulate failure
MONITOR_URL = os.environ.get('MONITOR_URL', 'http://localhost:8000/heartbeat')
BOT_ID = os.environ.get('BOT_ID', 'BOT-FAIL-' + str(random.randint(2000, 2999)))
HEARTBEATS = int(os.environ.get('HEARTBEATS', '5'))  # how many heartbeats to send before failing
INTERVAL = float(os.environ.get('INTERVAL', '3'))

print(f'Bot_fail {BOT_ID} -> {MONITOR_URL}, will send {HEARTBEATS} heartbeats (interval {INTERVAL}s)')
count = 0
while True:
    if count < HEARTBEATS:
        try:
            requests.post(MONITOR_URL, json={"botId": BOT_ID}, timeout=2)
            print(f'Heartbeat {count+1}/{HEARTBEATS} sent from {BOT_ID}')
        except Exception as e:
            print('Heartbeat error:', e)
    else:
        # simulate crash/stop: before stopping, send a failure JSON payload
        failure_payload = {
            "botId": BOT_ID,
            "error": f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] OCRFailure: PDF extraction returned null for page 8; engine raised DecryptionError",
            "dom": "<html><body><img id='scan' src='data:image/png;base64,...'/></body></html>",
            "last_action": "Wait for Element",
            "failure_type": "OCRFailure",
            "strategy": "RunOCREngine",
            "priority": "Medium"
        }
        try:
            # send to the monitor's failure report endpoint
            rf_url = MONITOR_URL.replace('/heartbeat', '/report_failure')
            requests.post(rf_url, json=failure_payload, timeout=2)
            print(f'Failure payload sent for {BOT_ID}')
        except Exception as e:
            print('Failed to send failure payload:', e)
        print(f'{BOT_ID} simulating failure (stopped heartbeats)')
        break
    count += 1
    time.sleep(INTERVAL)

# keep process alive to simulate crashed process (optionally exit)
# time.sleep(99999)
