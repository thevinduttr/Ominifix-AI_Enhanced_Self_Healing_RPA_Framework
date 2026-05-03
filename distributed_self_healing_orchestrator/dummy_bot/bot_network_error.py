import os
import time
import requests

# Dedicated network-error simulation bot.
MONITOR_URL = os.environ.get("MONITOR_URL", "http://localhost:8000/heartbeat")
BOT_ID = os.environ.get("BOT_ID", "BOT-NETWORK-ERROR-001")
HEARTBEATS = int(os.environ.get("HEARTBEATS", "4"))
INTERVAL = float(os.environ.get("INTERVAL", "3"))
ERROR_MESSAGE = os.environ.get(
    "NETWORK_ERROR_MESSAGE",
    "Connection timed out while calling upstream service"
)


def send_heartbeat(counter: int) -> None:
    payload = {
        "botId": BOT_ID,
        "meta": {
            "instance": "bot_network_error",
            "counter": counter,
        },
    }
    requests.post(MONITOR_URL, json=payload, timeout=2)


def send_network_failure() -> None:
    report_failure_url = MONITOR_URL.replace("/heartbeat", "/report_failure")
    failure_payload = {
        "botId": BOT_ID,
        "page_url": "https://dummy.local/api/payments",
        "failure_type": "NETWORK_ERROR",
        "failed_action": "request",
        "element_role": "api_call",
        "expected_text": "HTTP 200",
        "old_locator": "https://dummy.local/api/payments",
        "old_locator_type": "url",
        "error_message": ERROR_MESSAGE,
        "page_html": "",
        "screenshot_path": "",
        "metadata": {
            "bot_id": BOT_ID,
            "workflow_step": "submit_payment",
            "run_id": f"RUN-{BOT_ID}-NETWORK",
            "error_type": "NETWORK_ERROR",
            "source": "dummy_bot",
        },
    }
    requests.post(report_failure_url, json=failure_payload, timeout=3)


if __name__ == "__main__":
    print(
        f"bot_network_error started: BOT_ID={BOT_ID}, MONITOR_URL={MONITOR_URL}, "
        f"HEARTBEATS={HEARTBEATS}, INTERVAL={INTERVAL}s"
    )

    for i in range(1, HEARTBEATS + 1):
        try:
            send_heartbeat(i)
            print(f"Heartbeat {i}/{HEARTBEATS} sent from {BOT_ID}")
        except Exception as exc:
            print(f"Heartbeat error from {BOT_ID}: {exc}")
        time.sleep(INTERVAL)

    try:
        send_network_failure()
        print(f"NETWORK_ERROR payload sent from {BOT_ID}")
    except Exception as exc:
        print(f"Failed to send network failure payload from {BOT_ID}: {exc}")

    print(f"{BOT_ID} simulated network failure and stopped heartbeats.")
