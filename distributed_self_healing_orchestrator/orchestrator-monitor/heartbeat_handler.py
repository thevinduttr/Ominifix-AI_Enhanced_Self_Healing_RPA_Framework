import time
import threading
import os
import requests
from mq import publish_failure_event

DEFAULT_MODEL_URL = "https://rpa-error-classifier-555972249634.us-central1.run.app/predict"
MODEL_READ_TIMEOUT_SECONDS = float(os.environ.get("MODEL_READ_TIMEOUT_SECONDS", "20"))
MODEL_MAX_RETRIES = int(os.environ.get("MODEL_MAX_RETRIES", "2"))
DEFAULT_LOCATOR_ENGINE_URL = os.environ.get('LOCATOR_ENGINE_URL', 'http://ai_element_locator:8001/element-locator/report')
LOCATOR_READ_TIMEOUT_SECONDS = float(os.environ.get("LOCATOR_READ_TIMEOUT_SECONDS", "20"))

# Current known bots and recent failures
bots = {}
failures = []  # list of failure dicts with details


def _normalize_locator_category(raw_value):
    if raw_value is None:
        return 'UNKNOWN'
    raw = str(raw_value).strip()
    normalized = raw.upper().replace(' ', '_')
    aliases = {
        'ELEMENTNOTFOUND': 'ELEMENT_NOT_VISIBLE',
        'ELEMENT_NOT_FOUND': 'ELEMENT_NOT_VISIBLE',
        'NO_SUCH_ELEMENT': 'ELEMENT_NOT_VISIBLE',
        'ELEMENTNOTINTERACTABLE': 'ELEMENT_NOT_VISIBLE',
        'STALEELEMENTREFERENCE': 'UI_SELECTOR_CHANGED',
    }
    return aliases.get(normalized, normalized)


def _should_send_to_locator(failure):
    category = failure.get('category')
    if category and str(category).strip().lower() not in {'pending', 'unknown'}:
        current = category
    else:
        current = failure.get('failure_type')
    normalized = _normalize_locator_category(current)
    return normalized in {'UI_SELECTOR_CHANGED', 'ELEMENT_NOT_VISIBLE'}


def _build_locator_payload(failure):
    metadata = failure.get('metadata') or {}
    return {
        'page_url': failure.get('page_url') or 'about:blank',
        'failure_type': failure.get('failure_type') or failure.get('category') or 'ELEMENT_NOT_VISIBLE',
        'failed_action': failure.get('failed_action') or failure.get('last_action') or 'click',
        'element_role': failure.get('element_role'),
        'expected_text': failure.get('expected_text'),
        'old_locator': failure.get('old_locator'),
        'old_locator_type': failure.get('old_locator_type'),
        'error_message': failure.get('error') or failure.get('error_message') or 'Failure detected',
        'page_html': failure.get('page_html') or failure.get('dom'),
        'screenshot_path': failure.get('screenshot_path'),
        'template_path': failure.get('template_path'),
        'metadata': {
            **metadata,
            'source': 'distributed_self_healing_orchestrator',
            'bot_id': failure.get('botId') or metadata.get('bot_id'),
            'classification': failure.get('category') or failure.get('failure_type'),
        }
    }


def _request_locator_report(failure):
    payload = _build_locator_payload(failure)
    try:
        resp = requests.post(
            DEFAULT_LOCATOR_ENGINE_URL,
            json=payload,
            timeout=(5, LOCATOR_READ_TIMEOUT_SECONDS),
        )
        if not resp.ok:
            failure['locator_error'] = f"HTTP {resp.status_code}: {resp.text[:200]}"
            return
        report = resp.json()
        failure['locator_report'] = report
        if isinstance(report, dict):
            metadata = report.get('metadata') or {}
            if metadata.get('report_id'):
                failure['locator_report_id'] = metadata.get('report_id')

        bid = failure.get('botId')
        if bid and bid in bots:
            b = bots[bid]
            if b.get('last_error') and b['last_error'].get('timestamp') == failure.get('timestamp'):
                b['last_error']['locator_report'] = failure.get('locator_report')
                if failure.get('locator_report_id'):
                    b['last_error']['locator_report_id'] = failure.get('locator_report_id')
                bots[bid] = b
    except Exception as e:
        failure['locator_error'] = str(e)


def _queue_locator_request(failure):
    if failure.get('_locator_requested'):
        return
    failure['_locator_requested'] = True
    threading.Thread(target=_request_locator_report, args=(failure,), daemon=True).start()


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
    model_url = os.environ.get('MODEL_URL') or DEFAULT_MODEL_URL
    if model_url:
        try:
            threading.Thread(target=_classify_failure, args=(model_url, failure), daemon=True).start()
            # optimistically set category to 'pending'
            failure['category'] = 'pending'
        except Exception:
            failure['category'] = 'unknown'

    if _should_send_to_locator(failure):
        _queue_locator_request(failure)

    return {'status': 'recorded'}


def _classify_failure(model_url, failure):
    """Call external model to classify the failure and attach result into the failure record.
    This runs in a background thread and updates the shared failures/bots structures in-place.
    The model expects: error_message, retry_count, exec_time_ms, ui_change_score, network_latency
    """
    cat = 'unknown'
    confidence = None
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
        resp = None
        last_error = None
        for attempt in range(1, MODEL_MAX_RETRIES + 1):
            try:
                resp = requests.post(
                    model_url,
                    json=payload,
                    timeout=(5, MODEL_READ_TIMEOUT_SECONDS),
                )
                break
            except requests.RequestException as e:
                last_error = e
                print(f"[classifier] attempt {attempt}/{MODEL_MAX_RETRIES} failed: {e}")
                if attempt < MODEL_MAX_RETRIES:
                    time.sleep(attempt)

        if resp is None:
            raise requests.RequestException(last_error or "No response from model server")

        status = getattr(resp, 'status_code', None)
        try:
            body = resp.text
        except Exception:
            body = '<no-body>'
        print(f"[classifier] response status={status} body={body}")

        if resp.ok:
            try:
                j = resp.json()
            except Exception as e:
                print(f"[classifier] failed to parse JSON response: {e}")
                j = None
            if j is None:
                cat = 'unknown'
            else:
                # prefer common keys - support cloud model response shape
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

        if _should_send_to_locator(failure):
            _queue_locator_request(failure)

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
