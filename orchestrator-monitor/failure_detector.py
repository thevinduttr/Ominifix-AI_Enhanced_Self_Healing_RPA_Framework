import time
import threading
from mq import publish_failure_event
from heartbeat_handler import bots, failures


def monitor_bots():
    while True:
        now = time.time()
        for bot_id, info in list(bots.items()):
            last = info.get("last_seen", 0)
            # if not seen for threshold, mark failed and publish event
            if now - last > 10 and info.get("status") != "FAILED":
                print("Bot FAILED:", bot_id)
                # mark as failed
                info["status"] = "FAILED"
                info["failed_at"] = now
                bots[bot_id] = info
                # record failure
                failures.insert(0, {"botId": bot_id, "timestamp": now})
                # keep failures bounded
                if len(failures) > 50:
                    failures.pop()
                # publish to message queue
                try:
                    publish_failure_event(bot_id)
                except Exception:
                    print("Failed to publish failure event for", bot_id)
        time.sleep(5)


def start_failure_detection():
    thread = threading.Thread(target=monitor_bots)
    thread.daemon = True
    thread.start()
