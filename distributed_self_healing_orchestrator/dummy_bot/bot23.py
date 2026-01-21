import requests
import time
import random
import os

# Second bot: configurable monitor URL and BOT_ID
MONITOR_URL = os.environ.get('MONITOR_URL', 'http://localhost:8000/heartbeat')
bot_id = os.environ.get('BOT_ID', 'BOT-23')

print('Bot2 sending heartbeats to', MONITOR_URL)
while True:
    try:
        # Send an extra field to demonstrate flexibility
        requests.post(MONITOR_URL, json={"botId": bot_id, "meta": {"instance": "bot3"}}, timeout=2)
        print("Heartbeat sent from bot2:", bot_id)
    except Exception as e:
        print('Heartbeat error (bot2):', e)
    time.sleep(4)
