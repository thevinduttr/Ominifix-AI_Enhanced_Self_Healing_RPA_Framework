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
        # send additional CSV-style Selenium errors (if any)
        csv_failures = [
            "365be480-6700-49e9-9aee-e05575be2a36,2025-11-29T00:39:16.375075,Error: page.evaluate(): ExecutionContext destroyed,<section><button class='submit'>Submit</button></section>,type()(input[name='email']),selenium-bot-1,Low,JSExecutionErro",
            "25a00978-0bc6-471a-9f88-d17e51b0ec0c,2025-11-28T23:47:16.375075,AssertionError: expected text 'Success' but found 'Error',<div class='login'><input id='password'/><button id='login-btn'>Login</button></div>,click()(input[name='email']),automation-node-02,High,AssertionFailure"
        ]
        for line in csv_failures:
            try:
                parts = line.split(',', 7)
                if len(parts) < 8:
                    print('Skipping malformed csv failure:', line)
                    continue
                _, ts, err_msg, dom_snip, action, botname, priority, ftype = parts
                extra_payload = {
                    'botId': botname,
                    'error': err_msg,
                    'dom': dom_snip,
                    'last_action': action,
                    'failure_type': ftype,
                    'strategy': 'JSExecution',
                    'priority': priority
                }
                requests.post(rf_url, json=extra_payload, timeout=2)
                print(f'CSV failure sent for {botname}: {ftype}')
            except Exception as e:
                print('Failed to send csv failure line:', e)
        # also send the user-provided CSV-style Selenium error payloads (one or more)
        try:
            csv_lines = [
                "365be480-6700-49e9-9aee-e05575be2a36,2025-11-29T00:39:16.375075,Error: page.evaluate(): ExecutionContext destroyed,<section><button class='submit'>Submit</button></section>,type()(input[name='email']),selenium-bot-1,Low,JSExecutionErro",
                "25a00978-0bc6-471a-9f88-d17e51b0ec0c,2025-11-28T23:47:16.375075,AssertionError: expected text 'Success' but found 'Error',<div class='login'><input id='password'/><button id='login-btn'>Login</button></div>,click()(input[name='email']),automation-node-02,High,AssertionFailure"
            ]
            for csv_line in csv_lines:
                parts = csv_line.split(',', 7)
                if len(parts) == 8:
                    uid, ts, err_msg, dom_html, selector, csv_botid, priority, ftype = parts
                    csv_payload = {
                        "botId": csv_botid,
                        "error": err_msg,
                        "dom": dom_html,
                        "last_action": selector,
                        "failure_type": ftype or 'JSExecutionError',
                        "strategy": 'JSExecution',
                        "priority": priority,
                        "external_id": uid,
                        "reported_at": ts
                    }
                    try:
                        requests.post(rf_url, json=csv_payload, timeout=2)
                        print(f'CSV-style failure payload sent for {csv_botid}')
                    except Exception as e:
                        print('Failed to send CSV-style failure payload:', e)
                else:
                    print('CSV payload malformed, skipping:', csv_line)
        except Exception as e:
            print('Error preparing CSV payloads:', e)
        print(f'{BOT_ID} simulating failure (stopped heartbeats)')
        break
    count += 1
    time.sleep(INTERVAL)

# keep process alive to simulate crashed process (optionally exit)
# time.sleep(99999)
