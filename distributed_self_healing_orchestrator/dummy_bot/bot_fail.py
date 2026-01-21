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
        # include a Selenium-style traceback to mimic a browser-driven error
        selenium_trace = "Traceback (most recent call last):\n  File \"/usr/local/lib/python3.12/site-packages/selenium/webdriver/remote/remote_connection.py\", line 73, in execute\n    return self.command_executor.execute(driver_command, params)\n  File \"/usr/local/lib/python3.12/site-packages/selenium/webdriver/remote/http.py\", line 326, in execute\n    return self._request(command_info[0], url, body=data)\n  File \"/usr/local/lib/python3.12/site-packages/selenium/webdriver/remote/http.py\", line 348, in _request\n    resp = self.session.request(method, url, headers=headers, data=body, timeout=self._timeout)\n  File \"/usr/local/lib/python3.12/site-packages/requests/sessions.py\", line 587, in request\n    resp = self.send(prep, **send_kwargs)\nrequests.exceptions.ConnectionError: Message: unable to connect to renderer\n\nDuring handling of the above exception, another exception occurred:\n\nselenium.common.exceptions.WebDriverException: Message: element not interactable\n"

        failure_payload = {
            "botId": BOT_ID,
            "error": f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] SeleniumError: element not interactable\n{selenium_trace}",
            "dom": "<html><body><button id='submit'>Submit</button><div id='status'>Loading...</div></body></html>",
            "last_action": "Click #submit",
            "failure_type": "SeleniumError",
            "strategy": "RetryClick",
            "priority": "High"
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
