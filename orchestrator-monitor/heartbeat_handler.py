import time
from mq import publish_failure_event

# Current known bots and recent failures
bots = {}
failures = []  # list of failure dicts with details


def process_heartbeat(data):
    bot_id = data.get("botId")
    if not bot_id:
        return {"status": "error", "reason": "missing botId"}

    # Update last seen and mark running
    now = time.time()
    info = bots.get(bot_id, {})
    info.update({
        "last_seen": now,
        "status": "RUNNING"
    })
    # Clear failure marker if present
    info.pop("failed_at", None)
    info.pop("last_error", None)
    bots[bot_id] = info
    return {"status": "received"}


def process_failure(data):
    bot_id = data.get('botId')
    if not bot_id:
        return {"status": "error", "reason": "missing botId"}

    now = time.time()
    # store failure details
    failure = {
        'botId': bot_id,
        'timestamp': now,
        'error': data.get('error'),
        'dom': data.get('dom'),
        'last_action': data.get('last_action'),
        'failure_type': data.get('failure_type'),
        'strategy': data.get('strategy'),
        'priority': data.get('priority')
    }

    # mark bot as failed in bots dict
    info = bots.get(bot_id, {})
    info.update({
        'status': 'FAILED',
        'failed_at': now,
        'last_error': failure
    })
    bots[bot_id] = info

    # add to failures log
    failures.insert(0, failure)
    if len(failures) > 200:
        failures.pop()

    # notify coordinator via MQ
    try:
        publish_failure_event(bot_id)
    except Exception:
        pass

    return {'status': 'recorded'}
