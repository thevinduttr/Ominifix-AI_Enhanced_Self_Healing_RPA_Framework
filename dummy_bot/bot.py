import requests
import time
import random
import os

# Allow monitor URL to be set via env var for local testing
MONITOR_URL = os.environ.get('MONITOR_URL', 'http://localhost:8000/heartbeat')
bot_id = os.environ.get('BOT_ID', 'BOT-' + str(random.randint(100, 999)))

print('Sending heartbeats to', MONITOR_URL)
while True:
    try:
        requests.post(MONITOR_URL, json={"botId": bot_id}, timeout=2)
        print("Heartbeat sent:", bot_id)
    except Exception as e:
        print('Heartbeat error:', e)
    time.sleep(3)
