import os
import threading
from datetime import datetime

import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

APP_URL = "https://realwesiteforrpac.vercel.app/"
SLOW_MO_MS = 700
STEP_PAUSE_MS = 500
BOT_ID = "RPA-0020"
MONITOR_URL = os.getenv("MONITOR_URL", "http://localhost:8000/heartbeat")
HEARTBEAT_INTERVAL = float(os.getenv("HEARTBEAT_INTERVAL", "3"))
HEARTBEAT_ENABLED = os.getenv("HEARTBEAT_ENABLED", "true").strip().lower() in {"1", "true", "yes"}
FAILURE_WEBHOOK_URL = os.getenv("BOT_FAILURE_WEBHOOK_URL", "")
FAILURE_SNAPSHOT_DIR = "rpa"

CUSTOMER_DATA = {
    "fullName": "Ruwan Jayasinghe",
    "accountNumber": "300778899112",
    "accountType": "Savings",
    "branch": "Galle Branch",
    "phone": "0764455667",
    "email": "ruwan.jayasinghe@example.com",
    "balance": "875000",
    "kycVerified": True,
}

SELECTORS = {
    "form_title": "main .content-grid article.panel h2#customer-form-title",
    "full_name": "main .content-grid article.panel form.form-grid input[name='fullName']",
    "account_number": "main .content-grid article.panel form.form-grid input[name='accountNumber']",
    "account_type": "main .content-grid article.panel form.form-grid select[name='accountType']",
    "branch": "main .content-grid article.panel form.form-grid input[name='branch']",
    "phone": "main .content-grid article.panel form.form-grid input[name='phone']",
    "email": "main .content-grid article.panel form.form-grid input[name='email']",
    "balance": "main .content-grid article.panel form.form-grid input[name='balance']",
    "kyc_verified": "main .content-grid article.panel form.form-grid input[name='kycVerified']",
    "submit_button": "main .content-grid article.panel form.form-grid .button-row button[type='submit_not_exist']",
    "status": "main .content-grid article.panel .status",
    "records_rows": "main .content-grid article.panel .table-wrap tbody tr",
}


def build_failure_payload(page, exc: Exception) -> dict:
    page_url = "https://dummy.local/details"
    page_html = (
        '<!doctype html><html><body><div class="card"><a id="view_details_link" class="btn primary">View details</a></div></body></html>'
    )
    screenshot_path = ""

    if page is not None:
        if page.url:
            page_url = page.url

        try:
            page_html = page.content()
        except Exception:
            pass

        try:
            os.makedirs(FAILURE_SNAPSHOT_DIR, exist_ok=True)
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            screenshot_path = os.path.join(FAILURE_SNAPSHOT_DIR, f"failure_{timestamp}.png")
            page.screenshot(path=screenshot_path, full_page=True)
        except Exception:
            screenshot_path = ""

    failure_type = "ElementNotFound"
    if isinstance(exc, PlaywrightTimeoutError):
        # Playwright reports missing locator clicks as timeout after waiting.
        message = str(exc).lower()
        if "waiting for locator" in message or "locator.click" in message:
            failure_type = "ELEMENT_NOT_FOUND"
        else:
            failure_type = "TimeoutError"

    return {
        "botId": BOT_ID,
        "page_url": page_url,
        "failure_type": failure_type,
        "error": str(exc) or "No node found for selector",
        "last_action": "click",
        "failed_action": "click",
        "element_role": "primary_action",
        "expected_text": "Add Customer",
        "old_locator": SELECTORS["submit_button"],
        "old_locator_type": "css",
        "error_message": str(exc) or "No node found for selector",
        "dom": page_html,
        "page_html": page_html,
        "screenshot_path": screenshot_path,
        "metadata": {
            "bot_id": BOT_ID,
            "workflow_step": "open_details",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error_type": failure_type,
            "run_id": f"RUN-PP1-BUTTON-TO-A-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        },
    }


def failure_targets() -> list[str]:
    targets: list[str] = []

    if FAILURE_WEBHOOK_URL:
        targets.append(FAILURE_WEBHOOK_URL)

    if MONITOR_URL and "/heartbeat" in MONITOR_URL:
        targets.append(MONITOR_URL.replace("/heartbeat", "/report_failure"))

    if "localhost" in MONITOR_URL:
        targets.append("http://orchestrator_monitor:8000/report_failure")

    seen = set()
    deduped = []
    for url in targets:
        if url not in seen:
            deduped.append(url)
            seen.add(url)
    return deduped


def send_failure_payload(payload: dict) -> None:
    last_error = None
    for target in failure_targets():
        try:
            response = requests.post(target, json=payload, timeout=15)
            response.raise_for_status()
            print(f"Failure payload sent to {target}")
            return
        except Exception as exc:
            last_error = exc

    print("Could not send failure payload to any target.")
    print(f"Last failure payload error: {last_error}")
    print(payload)


def heartbeat_targets() -> list[str]:
    targets: list[str] = []

    if MONITOR_URL:
        targets.append(MONITOR_URL)

    if FAILURE_WEBHOOK_URL and "/report_failure" in FAILURE_WEBHOOK_URL:
        targets.append(FAILURE_WEBHOOK_URL.replace("/report_failure", "/heartbeat"))

    if "localhost" in MONITOR_URL:
        targets.append("http://orchestrator_monitor:8000/heartbeat")

    # Keep order and remove duplicates.
    seen = set()
    deduped = []
    for url in targets:
        if url not in seen:
            deduped.append(url)
            seen.add(url)
    return deduped


def send_heartbeat() -> None:
    payload = {
        "botId": BOT_ID,
        "meta": {
            "instance": "form_filler_bot",
            "app_url": APP_URL,
        },
    }

    last_error = None
    for target in heartbeat_targets():
        try:
            response = requests.post(target, json=payload, timeout=3)
            response.raise_for_status()
            print(f"Heartbeat sent from {BOT_ID} to {target}")
            return
        except Exception as exc:
            last_error = exc

    raise RuntimeError(f"All heartbeat targets failed. Last error: {last_error}")


def heartbeat_loop(stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        try:
            send_heartbeat()
        except Exception as exc:
            print(f"Heartbeat error from {BOT_ID}: {exc}")
        stop_event.wait(HEARTBEAT_INTERVAL)


def run() -> None:
    stop_event = threading.Event()
    heartbeat_thread = None
    if HEARTBEAT_ENABLED:
        heartbeat_thread = threading.Thread(target=heartbeat_loop, args=(stop_event,), daemon=True)
        heartbeat_thread.start()
    else:
        print("Heartbeat disabled via HEARTBEAT_ENABLED=false")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=SLOW_MO_MS)
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        try:
            page.goto(APP_URL, wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_selector(SELECTORS["form_title"], timeout=10_000)
            page.wait_for_timeout(STEP_PAUSE_MS)

            page.fill(SELECTORS["full_name"], CUSTOMER_DATA["fullName"])
            page.wait_for_timeout(STEP_PAUSE_MS)
            page.fill(SELECTORS["account_number"], CUSTOMER_DATA["accountNumber"])
            page.wait_for_timeout(STEP_PAUSE_MS)
            page.select_option(SELECTORS["account_type"], CUSTOMER_DATA["accountType"])
            page.wait_for_timeout(STEP_PAUSE_MS)
            page.fill(SELECTORS["branch"], CUSTOMER_DATA["branch"])
            page.wait_for_timeout(STEP_PAUSE_MS)
            page.fill(SELECTORS["phone"], CUSTOMER_DATA["phone"])
            page.wait_for_timeout(STEP_PAUSE_MS)
            page.fill(SELECTORS["email"], CUSTOMER_DATA["email"])
            page.wait_for_timeout(STEP_PAUSE_MS)
            page.fill(SELECTORS["balance"], CUSTOMER_DATA["balance"])
            page.wait_for_timeout(STEP_PAUSE_MS)

            checkbox = page.locator(SELECTORS["kyc_verified"])
            if CUSTOMER_DATA["kycVerified"] and not checkbox.is_checked():
                checkbox.check()
            if not CUSTOMER_DATA["kycVerified"] and checkbox.is_checked():
                checkbox.uncheck()
            page.wait_for_timeout(STEP_PAUSE_MS)

            page.locator(SELECTORS["submit_button"]).click()

            page.locator(SELECTORS["status"]).filter(has_text="New customer added successfully.").wait_for(
                state="visible",
                timeout=10_000,
            )

            page.locator(SELECTORS["records_rows"]).filter(
                has_text=CUSTOMER_DATA["accountNumber"]
            ).first.wait_for(
                state="visible",
                timeout=10_000,
            )

            print("RPA bot finished: customer form submitted and record verified.")

        except Exception as exc:
            # Stop heartbeats immediately when the bot fails.
            stop_event.set()
            if heartbeat_thread is not None:
                heartbeat_thread.join(timeout=2)

            if isinstance(exc, PlaywrightTimeoutError):
                print("RPA bot failed due to timeout. Check if the app is running on http://localhost:5173")
            else:
                print("RPA bot failed due to an unexpected exception.")

            print(f"Details: {exc}")

            try:
                failure_payload = build_failure_payload(page, exc)
                send_failure_payload(failure_payload)
            except Exception as payload_exc:
                print("Could not send failure payload.")
                print(f"Payload error: {payload_exc}")
        finally:
            stop_event.set()
            if heartbeat_thread is not None:
                heartbeat_thread.join(timeout=2)
            page.wait_for_timeout(1500)
            browser.close()


if __name__ == "__main__":
    run()
