import time
import threading
from mq import publish_failure_event
from heartbeat_handler import bots

def monitor_bots():
    while True:
        now = time.time()
        for bot_id, info in bots.items():
            if now - info["last_seen"] > 10:
                print("Bot FAILED:", bot_id)
                publish_failure_event(bot_id)
        time.sleep(5)

def start_failure_detection():
    thread = threading.Thread(target=monitor_bots)
    thread.daemon = True
    thread.start()
