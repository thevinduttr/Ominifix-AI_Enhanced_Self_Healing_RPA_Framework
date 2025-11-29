import time

bots = {}

def process_heartbeat(data):
    bot_id = data["botId"]
    bots[bot_id] = {
        "last_seen": time.time(),
        "status": "RUNNING"
    }
    return {"status": "received"}
