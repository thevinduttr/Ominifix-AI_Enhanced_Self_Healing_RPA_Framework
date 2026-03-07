import os
import random
import time

import requests

# Sends regular heartbeats and periodically reports AUTHENTICATION_ERROR failures.
MONITOR_URL = os.environ.get("MONITOR_URL", "http://localhost:8000/heartbeat")
BOT_ID = os.environ.get("BOT_ID", f"BOT-AUTH-{random.randint(3000, 3999)}")
HEARTBEAT_INTERVAL = float(os.environ.get("HEARTBEAT_INTERVAL", "3"))
FAILURE_EVERY = int(os.environ.get("FAILURE_EVERY", "5"))

REPORT_FAILURE_URL = MONITOR_URL.replace("/heartbeat", "/report_failure")

AUTH_PAGE_URL = "https://dummy.local/login"
AUTH_PAGE_HTML = (
    "<form id='login_form'>"
    "<input id='username' name='username' />"
    "<input id='password' name='password' type='password' />"
    "<button id='sign_in_btn' class='btn primary'>Sign in</button>"
    "</form>"
)


def post_heartbeat() -> None:
    payload = {
        "botId": BOT_ID,
        "meta": {
            "instance": "bot_authentication_error",
        },
    }
    requests.post(MONITOR_URL, json=payload, timeout=2)


def post_auth_failure(cycle: int) -> None:
    run_id = f"RUN-AUTH-{cycle:04d}"
    failure_payload = {
        "botId": BOT_ID,
        "error": "AUTHENTICATION_ERROR: access token expired while calling protected API",
        "last_action": "authenticate_user",
        "failed_action": "authenticate_user",
        "failure_type": "AUTHENTICATION_ERROR",
        "strategy": "CredentialRefreshFlow",
        "priority": "High",
        "page_url": AUTH_PAGE_URL,
        "element_role": "login_action",
        "expected_text": "Sign in",
        "old_locator": "//button[@id='login']",
        "old_locator_type": "xpath",
        "page_html": AUTH_PAGE_HTML,
        "screenshot_path": None,
        "template_path": None,
        "metadata": {
            "bot_id": BOT_ID,
            "workflow_step": "authentication",
            "error_type": "AUTHENTICATION_ERROR",
            "cycle": cycle,
            "source": "dummy_bot",
            "run_id": run_id,
            "script_path": "data/scripts/broken/auto_generated.py",
            "failing_line": 1,
            "base_url": "https://dummy.local",
            "target_url": AUTH_PAGE_URL,
            "environment": "docker",
        },
    }
    requests.post(REPORT_FAILURE_URL, json=failure_payload, timeout=2)


if __name__ == "__main__":
    print(
        f"bot_authentication_error starting: BOT_ID={BOT_ID}, MONITOR_URL={MONITOR_URL}, "
        f"FAILURE_EVERY={FAILURE_EVERY}, HEARTBEAT_INTERVAL={HEARTBEAT_INTERVAL}s"
    )

    cycle = 0
    while True:
        cycle += 1
        try:
            post_heartbeat()
            print(f"Heartbeat sent from {BOT_ID} (cycle={cycle})")
        except Exception as exc:
            print("Heartbeat error:", exc)

        if FAILURE_EVERY > 0 and cycle % FAILURE_EVERY == 0:
            try:
                post_auth_failure(cycle)
                print(f"AUTHENTICATION_ERROR failure payload sent from {BOT_ID} (cycle={cycle})")
            except Exception as exc:
                print("Failure report error:", exc)

        time.sleep(HEARTBEAT_INTERVAL)
