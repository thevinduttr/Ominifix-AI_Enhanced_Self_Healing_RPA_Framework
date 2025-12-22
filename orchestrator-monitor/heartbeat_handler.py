import time
import threading
import os
import requests
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

    # kick off async classification using external model if configured
    model_url = os.environ.get('MODEL_URL')
    if model_url:
        try:
            threading.Thread(target=_classify_failure, args=(model_url, failure), daemon=True).start()
            # optimistically set category to 'pending'
            failure['category'] = 'pending'
        except Exception:
            failure['category'] = 'unknown'

    return {'status': 'recorded'}


def _classify_failure(model_url, failure):
    """Call external model to classify the failure and attach result into the failure record.
    This runs in a background thread and updates the shared failures/bots structures in-place.
    The model is expected to accept JSON and respond with JSON containing a `category` field.
    """
    try:
        payload = {
            'botId': failure.get('botId'),
            'error': failure.get('error'),
            'failure_type': failure.get('failure_type'),
            'last_action': failure.get('last_action'),
            'strategy': failure.get('strategy'),
            'priority': failure.get('priority')
        }
        print(f"[classifier] POST {model_url} payload keys={list(payload.keys())}")
        resp = requests.post(model_url, json=payload, timeout=5)
        status = getattr(resp, 'status_code', None)
        try:
            body = resp.text
        except Exception:
            body = '<no-body>'
        print(f"[classifier] response status={status} body={body}")

        confidence = None
        if resp.ok:
            try:
                j = resp.json()
            except Exception as e:
                print(f"[classifier] failed to parse JSON response: {e}")
                j = None
            if j is None:
                cat = 'unknown'
            else:
                # prefer common keys
                cat = j.get('category') or j.get('label') or j.get('prediction')
                if not cat:
                    # some models return a top-level result
                    cat = j
                # try to get confidence if present
                try:
                    confidence = j.get('confidence') if isinstance(j, dict) else None
                    # ensure numeric
                    if confidence is not None:
                        confidence = float(confidence)
                except Exception:
                    confidence = None
        else:
            print(f"[classifier] non-ok response: {status} body={body}")
            cat = 'unknown'
    except Exception as e:
        print(f"[classifier] request error: {e}")
        cat = 'unknown'

    # attach category back to the failure object (first attempt: mutate the object in failures list)
    try:
        # attach category and confidence into the recorded failure
        failure['category'] = cat
        if confidence is not None:
            failure['confidence'] = confidence

        # If the model is unknown or low-confidence, fall back to the original failure_type
        try:
            if (not cat or cat == 'unknown') or (isinstance(confidence, float) and confidence < 0.5):
                fb = failure.get('failure_type')
                if fb:
                    failure['category'] = fb
        except Exception:
            pass

        # if the bots dict holds last_error, update it too
        bid = failure.get('botId')
        if bid and bid in bots:
            b = bots[bid]
            if b.get('last_error') and b['last_error'].get('timestamp') == failure.get('timestamp'):
                b['last_error']['category'] = failure.get('category')
                if failure.get('confidence') is not None:
                    b['last_error']['confidence'] = failure.get('confidence')
                bots[bid] = b
    except Exception:
        pass
