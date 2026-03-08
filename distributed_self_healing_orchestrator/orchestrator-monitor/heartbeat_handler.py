import time
import threading
import os
import requests
import docker
from mq import publish_failure_event

DEFAULT_MODEL_URL = "https://rpa-error-classifier-555972249634.us-central1.run.app/predict"
MODEL_READ_TIMEOUT_SECONDS = float(os.environ.get("MODEL_READ_TIMEOUT_SECONDS", "20"))
MODEL_MAX_RETRIES = int(os.environ.get("MODEL_MAX_RETRIES", "2"))
DEFAULT_LOCATOR_ENGINE_URL = os.environ.get('LOCATOR_ENGINE_URL', 'http://ai_element_locator:8001/element-locator/report')
LOCATOR_READ_TIMEOUT_SECONDS = float(os.environ.get("LOCATOR_READ_TIMEOUT_SECONDS", "20"))
DEFAULT_HEALING_ENGINE_URL = os.environ.get('HEALING_ENGINE_URL', 'http://ai_rpa_healing_engine:8000/api/v1/heal')
HEALING_READ_TIMEOUT_SECONDS = float(os.environ.get("HEALING_READ_TIMEOUT_SECONDS", "30"))
DEFAULT_PTQA_URL = os.environ.get('PTQA_SERVICE_URL', 'http://ptqa_service:8000/ptqa/evaluate-healing')
PTQA_READ_TIMEOUT_SECONDS = float(os.environ.get("PTQA_READ_TIMEOUT_SECONDS", "30"))
PTQA_RESTART_DELAY_SECONDS = float(os.environ.get("PTQA_RESTART_DELAY_SECONDS", "3"))
RESTART_ONLY_ON_PTQA_APPROVAL = os.environ.get("RESTART_ONLY_ON_PTQA_APPROVAL", "true").strip().lower() in {"1", "true", "yes"}
NETWORK_ERROR_RESTART_MIN_CONFIDENCE_PERCENT = float(
    os.environ.get("NETWORK_ERROR_RESTART_MIN_CONFIDENCE_PERCENT", "51")
)
NETWORK_ERROR_AUTO_RESTART = os.environ.get(
    "NETWORK_ERROR_AUTO_RESTART",
    "true",
).strip().lower() in {"1", "true", "yes"}
FAILED_STATUS_HOLD_SECONDS = float(os.environ.get("FAILED_STATUS_HOLD_SECONDS", "12"))
RESTART_ON_CATEGORIES = {
    c.strip().upper()
    for c in os.environ.get(
        "RESTART_ON_CATEGORIES",
        "NETWORK_ERROR,UNKNOWN,BOT_ERROR",
    ).split(",")
    if c.strip()
}

# Current known bots and recent failures
bots = {}
failures = []  # list of failure dicts with details
_docker_client = None
PTQA_APPROVED_RECOMMENDATIONS = {
    "APPROVE_HEALING",
    "APPROVED",
    "APPROVE",
    "ALLOW",
}


def _parse_bot_service_map(raw_value):
    """Parse BOT_SERVICE_MAP like: RPA-0020:form_filler_bot,RPA-0030:other_service."""
    mapping = {}
    for pair in str(raw_value or "").split(","):
        token = pair.strip()
        if not token or ":" not in token:
            continue
        bot_id, service = token.split(":", 1)
        bot_id = bot_id.strip()
        service = service.strip()
        if bot_id and service:
            mapping[bot_id] = service
    return mapping


BOT_SERVICE_MAP = _parse_bot_service_map(os.environ.get("BOT_SERVICE_MAP", ""))


def _confidence_to_percent(value):
    """Normalize confidence values in [0..1] or [0..100] into percent."""
    try:
        n = float(value)
    except Exception:
        return None

    if n < 0:
        return None
    if n <= 1:
        return n * 100.0
    return n


def _should_restart_network_error_by_confidence(failure):
    category = (failure.get('category') or '').strip().upper()
    if category != 'NETWORK_ERROR':
        return False

    confidence_percent = _confidence_to_percent(failure.get('confidence'))
    if confidence_percent is None:
        return False

    return confidence_percent >= NETWORK_ERROR_RESTART_MIN_CONFIDENCE_PERCENT


def _is_network_error_failure(failure):
    category = _normalize_locator_category(failure.get('category'))
    failure_type = _normalize_locator_category(failure.get('failure_type'))
    return category == 'NETWORK_ERROR' or failure_type == 'NETWORK_ERROR'


def _extract_ptqa_recommendation(data):
    """Read recommendation from common payload shapes used by monitor/PTQA integration."""
    if not isinstance(data, dict):
        return ""

    # Preferred: nested PTQA result object.
    ptqa_result = data.get('ptqa_result')
    if isinstance(ptqa_result, dict):
        rec = str(ptqa_result.get('recommendation') or '').strip()
        if rec:
            return rec

    # Fallback: recommendation sent as a top-level field.
    return str(data.get('recommendation') or '').strip()


def _get_docker_client():
    global _docker_client
    if _docker_client is None:
        _docker_client = docker.from_env()
    return _docker_client


def _restart_bot_for_category(failure):
    is_network_error = _is_network_error_failure(failure)
    allow_network_restart = is_network_error and (
        NETWORK_ERROR_AUTO_RESTART or _should_restart_network_error_by_confidence(failure)
    )

    if RESTART_ONLY_ON_PTQA_APPROVAL and not allow_network_restart:
        return

    category = _normalize_locator_category(failure.get('category') or failure.get('failure_type'))
    if category not in RESTART_ON_CATEGORIES:
        return

    bot_id = failure.get('botId') or (failure.get('metadata') or {}).get('bot_id')
    if not bot_id:
        failure['bot_restart_error'] = 'missing botId'
        return

    try:
        metadata = failure.get('metadata') or {}
        service_hint = metadata.get('bot_service') or metadata.get('compose_service')
        container = _find_container_for_bot(bot_id, service_hint=service_hint)
        if container is None:
            failure['bot_restart_error'] = f"no container found for botId '{bot_id}'"
            return

        container.restart(timeout=10)
        service_name = (container.labels or {}).get('com.docker.compose.service') or container.name
        failure['bot_restart'] = {
            'requested': True,
            'category': category,
            'service': service_name,
            'container': container.name,
            'timestamp': time.time(),
            'status': 'restarted',
        }
        failure['bot_restart_error'] = None
    except Exception as e:
        failure['bot_restart_error'] = str(e)


def _find_container_for_bot(bot_id, service_hint=None):
    """Resolve container by hint/map, then compose service name, then BOT_ID env fallback."""
    client = _get_docker_client()

    # Preferred: explicit service hint from payload metadata or env map.
    hinted_service = (service_hint or "").strip() or BOT_SERVICE_MAP.get(bot_id, "")
    if hinted_service:
        hinted = client.containers.list(
            all=True,
            filters={"label": f"com.docker.compose.service={hinted_service}"},
        )
        if hinted:
            return hinted[0]

    # Fast path: botId matches compose service name.
    direct = client.containers.list(
        all=True,
        filters={"label": f"com.docker.compose.service={bot_id}"},
    )
    if direct:
        return direct[0]

    # Fallback: search compose containers by BOT_ID env.
    compose_containers = client.containers.list(
        all=True,
        filters={"label": "com.docker.compose.project"},
    )
    target_env = f"BOT_ID={bot_id}"
    for container in compose_containers:
        envs = ((container.attrs.get("Config") or {}).get("Env") or [])
        if target_env in envs:
            return container

    return None


def _restart_bot_on_ptqa_approval(failure, ptqa_result):
    if not isinstance(ptqa_result, dict):
        return

    # Prevent duplicate restarts for the same failure event.
    existing = failure.get('ptqa_restart') or {}
    if existing.get('status') == 'restarted':
        return

    recommendation = str(ptqa_result.get('recommendation') or '').strip().upper()
    if recommendation not in PTQA_APPROVED_RECOMMENDATIONS:
        return

    bot_id = failure.get('botId') or (failure.get('metadata') or {}).get('bot_id')
    if not bot_id:
        failure['ptqa_restart_error'] = 'missing botId'
        return

    try:
        metadata = failure.get('metadata') or {}
        service_hint = metadata.get('bot_service') or metadata.get('compose_service')
        container = _find_container_for_bot(bot_id, service_hint=service_hint)
        if container is None:
            if service_hint:
                failure['ptqa_restart_error'] = (
                    f"no container found for botId '{bot_id}' using service_hint '{service_hint}'"
                )
            elif BOT_SERVICE_MAP.get(bot_id):
                failure['ptqa_restart_error'] = (
                    f"no container found for botId '{bot_id}' using BOT_SERVICE_MAP service '{BOT_SERVICE_MAP.get(bot_id)}'"
                )
            else:
                failure['ptqa_restart_error'] = (
                    f"no container found for botId '{bot_id}'. "
                    f"Set metadata.bot_service or BOT_SERVICE_MAP={bot_id}:<compose_service>."
                )
            return

        service_name = (container.labels or {}).get('com.docker.compose.service') or container.name

        restart_delay = max(0.0, PTQA_RESTART_DELAY_SECONDS)
        if restart_delay > 0:
            time.sleep(restart_delay)

        container.restart(timeout=10)

        failure['ptqa_restart'] = {
            'requested': True,
            'trigger': 'PTQA_APPROVED',
            'recommendation': recommendation,
            'bot_id': bot_id,
            'service': service_name,
            'container': container.name,
            'delay_seconds': restart_delay,
            'timestamp': time.time(),
            'status': 'restarted',
        }
        failure['ptqa_restart_error'] = None
    except Exception as e:
        failure['ptqa_restart_error'] = str(e)


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
        'TIMEOUTERROR': 'TIMEOUT_ERROR',
        'TIMEOUT_EXCEPTION': 'TIMEOUT_ERROR',
    }
    return aliases.get(normalized, normalized)


def _should_send_to_locator(failure):
    category = failure.get('category')
    if category and str(category).strip().lower() not in {'pending', 'unknown'}:
        current = category
    else:
        current = failure.get('failure_type')
    normalized = _normalize_locator_category(current)
    return normalized in {'UI_SELECTOR_CHANGED', 'ELEMENT_NOT_VISIBLE', 'TIMEOUT_ERROR'}


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
        healing_result_payload = None
        if isinstance(report, dict):
            metadata = report.get('metadata') or {}
            if metadata.get('report_id'):
                failure['locator_report_id'] = metadata.get('report_id')

            # Carry healing details from locator->healing integration into orchestrator state.
            if 'healing_request' in report:
                failure['healing_request'] = report.get('healing_request')
            if 'healing_result' in report:
                failure['healing_result'] = report.get('healing_result')
                healing_result_payload = report.get('healing_result')
                hs = (report.get('healing_result') or {}).get('healing_summary') or {}
                if hs.get('status'):
                    failure['healing_status'] = hs.get('status')
                if hs.get('new_locator'):
                    failure['healed_locator'] = hs.get('new_locator')
            if report.get('healing_error'):
                failure['healing_error'] = report.get('healing_error')

        # Forward healing engine output to PTQA automatically.
        if healing_result_payload:
            try:
                ptqa_resp = requests.post(
                    DEFAULT_PTQA_URL,
                    json=healing_result_payload,
                    timeout=(5, PTQA_READ_TIMEOUT_SECONDS),
                )
                if ptqa_resp.ok:
                    failure['ptqa_result'] = ptqa_resp.json()
                    failure['ptqa_error'] = None
                    _restart_bot_on_ptqa_approval(failure, failure['ptqa_result'])
                else:
                    failure['ptqa_error'] = f"HTTP {ptqa_resp.status_code}: {ptqa_resp.text[:300]}"
            except Exception as ptqa_exc:
                failure['ptqa_error'] = str(ptqa_exc)

        bid = failure.get('botId')
        if bid and bid in bots:
            b = bots[bid]
            if b.get('last_error') and b['last_error'].get('timestamp') == failure.get('timestamp'):
                b['last_error']['locator_report'] = failure.get('locator_report')
                if failure.get('locator_report_id'):
                    b['last_error']['locator_report_id'] = failure.get('locator_report_id')
                if 'healing_request' in failure:
                    b['last_error']['healing_request'] = failure.get('healing_request')
                if 'healing_result' in failure:
                    b['last_error']['healing_result'] = failure.get('healing_result')
                if failure.get('healing_status'):
                    b['last_error']['healing_status'] = failure.get('healing_status')
                if failure.get('healed_locator'):
                    b['last_error']['healed_locator'] = failure.get('healed_locator')
                if failure.get('healing_error'):
                    b['last_error']['healing_error'] = failure.get('healing_error')
                if 'ptqa_result' in failure:
                    b['last_error']['ptqa_result'] = failure.get('ptqa_result')
                if failure.get('ptqa_error'):
                    b['last_error']['ptqa_error'] = failure.get('ptqa_error')
                if 'ptqa_restart' in failure:
                    b['last_error']['ptqa_restart'] = failure.get('ptqa_restart')
                if failure.get('ptqa_restart_error'):
                    b['last_error']['ptqa_restart_error'] = failure.get('ptqa_restart_error')
                bots[bid] = b
    except Exception as e:
        failure['locator_error'] = str(e)


def _build_direct_healing_payload(failure):
    metadata = failure.get('metadata') or {}
    ts = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    bot_id = failure.get('botId') or metadata.get('bot_id') or 'UNKNOWN_BOT'
    run_id = metadata.get('run_id', '')

    return {
        'metadata': {
            'schema_version': '1.0',
            'report_id': f"DIRECT-{int(failure.get('timestamp') or time.time())}",
            'run_id': run_id,
            'bot_id': bot_id,
            'timestamp': ts,
            'source_component': 'distributed_self_healing_orchestrator',
            'target_component': 'code_healing_engine',
            'environment': metadata.get('environment', ''),
        },
        'failure_context': {
            'script_path': metadata.get('script_path') or 'data/scripts/broken/auto_generated.py',
            'failing_line': int(metadata.get('failing_line') or 1),
            'action': failure.get('last_action') or 'authenticate_user',
            'old_locator': failure.get('old_locator') or '',
            'error_type': failure.get('failure_type') or failure.get('category') or 'AUTHENTICATION_ERROR',
            'error_message': failure.get('error') or 'Authentication failed',
        },
        'dom_context': {
            'new_element_html': failure.get('page_html') or failure.get('dom') or '',
            'page_url': failure.get('page_url') or metadata.get('target_url') or '',
            'page_name': metadata.get('page_name') or '',
        },
        'element_expectation': {
            'expected_role': failure.get('element_role') or 'login_form',
            'expected_text': failure.get('expected_text') or 'Login',
        },
        'element_candidate': None,
    }


def _request_direct_healing(failure):
    payload = _build_direct_healing_payload(failure)
    try:
        resp = requests.post(
            DEFAULT_HEALING_ENGINE_URL,
            json=payload,
            timeout=(5, HEALING_READ_TIMEOUT_SECONDS),
        )
        if not resp.ok:
            failure['healing_error'] = f"HTTP {resp.status_code}: {resp.text[:300]}"
            return

        healing_result = resp.json()
        failure['healing_request'] = payload
        failure['healing_result'] = healing_result
        failure['healing_error'] = None

        hs = (healing_result or {}).get('healing_summary') or {}
        if hs.get('status'):
            failure['healing_status'] = hs.get('status')
        if hs.get('new_locator'):
            failure['healed_locator'] = hs.get('new_locator')

        try:
            ptqa_resp = requests.post(
                DEFAULT_PTQA_URL,
                json=healing_result,
                timeout=(5, PTQA_READ_TIMEOUT_SECONDS),
            )
            if ptqa_resp.ok:
                failure['ptqa_result'] = ptqa_resp.json()
                failure['ptqa_error'] = None
                _restart_bot_on_ptqa_approval(failure, failure['ptqa_result'])
            else:
                failure['ptqa_error'] = f"HTTP {ptqa_resp.status_code}: {ptqa_resp.text[:300]}"
        except Exception as ptqa_exc:
            failure['ptqa_error'] = str(ptqa_exc)

        bid = failure.get('botId')
        if bid and bid in bots:
            b = bots[bid]
            if b.get('last_error') and b['last_error'].get('timestamp') == failure.get('timestamp'):
                b['last_error']['healing_request'] = failure.get('healing_request')
                b['last_error']['healing_result'] = failure.get('healing_result')
                b['last_error']['healing_error'] = failure.get('healing_error')
                if failure.get('healing_status'):
                    b['last_error']['healing_status'] = failure.get('healing_status')
                if failure.get('healed_locator'):
                    b['last_error']['healed_locator'] = failure.get('healed_locator')
                if 'ptqa_result' in failure:
                    b['last_error']['ptqa_result'] = failure.get('ptqa_result')
                if failure.get('ptqa_error'):
                    b['last_error']['ptqa_error'] = failure.get('ptqa_error')
                if 'ptqa_restart' in failure:
                    b['last_error']['ptqa_restart'] = failure.get('ptqa_restart')
                if failure.get('ptqa_restart_error'):
                    b['last_error']['ptqa_restart_error'] = failure.get('ptqa_restart_error')
                bots[bid] = b
    except Exception as e:
        failure['healing_error'] = str(e)


def _queue_direct_healing_request(failure):
    if failure.get('_healing_requested'):
        return
    failure['_healing_requested'] = True
    threading.Thread(target=_request_direct_healing, args=(failure,), daemon=True).start()


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

    # Keep FAILED visible briefly so fast auto-restarts don't hide it in UI.
    failed_at = info.get("failed_at")
    if info.get("status") == "FAILED" and failed_at is not None:
        elapsed = now - float(failed_at)
        if elapsed < max(0.0, FAILED_STATUS_HOLD_SECONDS):
            info["last_seen"] = now
            bots[bot_id] = info
            return {
                "status": "received",
                "state": "FAILED_HOLD",
                "hold_seconds_remaining": round(max(0.0, FAILED_STATUS_HOLD_SECONDS - elapsed), 2),
            }

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

    # Preserve recommendation payload when it is already available at report time.
    if isinstance(data.get('ptqa_result'), dict):
        failure['ptqa_result'] = data.get('ptqa_result')
    incoming_recommendation = _extract_ptqa_recommendation(data)
    if incoming_recommendation and 'ptqa_result' not in failure:
        failure['ptqa_result'] = {'recommendation': incoming_recommendation}
    
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

    # Direct healing path for auth failures (locator is intentionally skipped).
    category = _normalize_locator_category(failure.get('failure_type') or failure.get('category'))
    if category == 'AUTHENTICATION_ERROR':
        _queue_direct_healing_request(failure)

    # Restart is intentionally triggered only after PTQA service evaluation response.

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

        # Only fallback if model returned nothing (do NOT override explicit UNKNOWN).
        try:
            if not cat:
                if original_ft:
                    failure['category'] = original_ft
                    failure['failure_type'] = original_ft
        except Exception:
            pass

        _restart_bot_for_category(failure)

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
                if failure.get('bot_restart'):
                    b['last_error']['bot_restart'] = failure.get('bot_restart')
                if failure.get('bot_restart_error'):
                    b['last_error']['bot_restart_error'] = failure.get('bot_restart_error')
                bots[bid] = b
    except Exception:
        pass
