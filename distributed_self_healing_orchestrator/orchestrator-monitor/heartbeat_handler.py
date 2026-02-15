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

    print(f"🔍 process_failure() received keys: {list(data.keys())}")
    print(f"🔍 Data has page_url: {data.get('page_url')}")
    
    now = time.time()
    # store failure details with all comprehensive fields
    failure = {
        'botId': bot_id,
        'timestamp': now,
        'error': data.get('error') or data.get('error_message'),  # Support both field names
        'dom': data.get('dom'),
        'last_action': data.get('last_action') or data.get('failed_action'),  # Support both field names
        'failure_type': data.get('failure_type'),
        'strategy': data.get('strategy'),
        'priority': data.get('priority'),
        # Comprehensive fields from enhanced bot
        'page_url': data.get('page_url'),
        'element_role': data.get('element_role'),
        'expected_text': data.get('expected_text'),
        'old_locator': data.get('old_locator'),
        'old_locator_type': data.get('old_locator_type'),
        'page_html': data.get('page_html'),
        'screenshot_path': data.get('screenshot_path'),
        'metadata': data.get('metadata')
    }
    
    print(f"🔍 Created failure object with keys: {list(failure.keys())}")
    print(f"🔍 Failure has page_url: {failure.get('page_url')}")

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
    
    print(f"🔍 Added to failures list. Current failures[0] keys: {list(failures[0].keys())}")

    # notify coordinator via MQ
    try:
        publish_failure_event(bot_id)
    except Exception:
        pass

    # kick off async classification using external model if configured
    model_url = os.environ.get('MODEL_URL') or 'http://localhost:8090/predict'
    if model_url:
        try:
            threading.Thread(target=_classify_failure, args=(model_url, failure), daemon=True).start()
            # optimistically set category to 'pending'
            failure['category'] = 'pending'
        except Exception:
            failure['category'] = 'unknowng'

    return {'status': 'recorded'}


def _classify_failure(model_url, failure):
    """Call external model to classify the failure and attach result into the failure record.
    This runs in a background thread and updates the shared failures/bots structures in-place.
    The model expects: error_message, retry_count, exec_time_ms, ui_change_score, network_latency
    """
    try:
        # Extract metadata for your model's expected format
        metadata = failure.get('metadata') or {}
        error_msg = failure.get('error') or failure.get('error_message') or 'Unknown error'
        
        # Map failure data to your model's input format
        payload = {
            'error_message': error_msg,
            'retry_count': metadata.get('retry_count', 1),  # default to 1 if not provided
            'exec_time_ms': metadata.get('exec_time_ms', 5000),  # default 5s
            'ui_change_score': metadata.get('ui_change_score', 0.5),  # neutral default
            'network_latency': metadata.get('network_latency', 100)  # default 100ms
        }
        print(f"[classifier] POST {model_url} payload={payload}")
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
                # prefer common keys - support error_class_name for user's custom model
                cat = j.get('category') or j.get('label') or j.get('prediction') or j.get('error_class_name')
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
        original_ft = failure.get('failure_type')
        failure['category'] = cat
        # reflect the model label as failure_type so UI shows model output directly
        if cat:
            failure['failure_type'] = cat
        if confidence is not None:
            failure['confidence'] = confidence

        # Only fallback if model returned nothing/unknown (do NOT override on low confidence)
        try:
            if not cat or cat == 'unknown':
                if original_ft:
                    failure['category'] = original_ft
                    failure['failure_type'] = original_ft
        except Exception:
            pass

        # if the bots dict holds last_error, update it too
        bid = failure.get('botId')
        if bid and bid in bots:
            b = bots[bid]
            if b.get('last_error') and b['last_error'].get('timestamp') == failure.get('timestamp'):
                b['last_error']['category'] = failure.get('category')
                if failure.get('failure_type'):
                    b['last_error']['failure_type'] = failure.get('failure_type')
                if failure.get('confidence') is not None:
                    b['last_error']['confidence'] = failure.get('confidence')
                bots[bid] = b
    except Exception:
        pass
