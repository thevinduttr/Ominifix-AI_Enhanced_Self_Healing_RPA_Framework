import os
import threading
import time
from datetime import datetime, UTC
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

url = "http://localhost:5174"
BOT_ID = "DUMMY-BOT-new"
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8000")
HEARTBEAT_INTERVAL_SECONDS = 5
bot_running = True  # Flag to control heartbeat


def send_heartbeat():
    """Send heartbeat to orchestrator every 5 seconds until bot stops."""
    global bot_running
    while bot_running:
        try:
            payload = {
                "botId": BOT_ID,
                "metadata": {
                    "bot_service": "dummy_bot",
                    "run_id": f"RUN-DUMMY-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
                }
            }
            response = requests.post(
                f"{ORCHESTRATOR_URL}/heartbeat",
                json=payload,
                timeout=5
            )
            print(f"✓ Heartbeat sent: {response.status_code}")
        except Exception as e:
            print(f"✗ Heartbeat failed: {e}")
        time.sleep(HEARTBEAT_INTERVAL_SECONDS)


def send_failure_report(page, exc: Exception) -> None:
    """Send failure details to orchestrator."""
    try:
        page_url = page.url if page else "unknown"
        page_html = page.content() if page else ""
        
        # Capture screenshot
        screenshot_path = ""
        try:
            os.makedirs("rpa", exist_ok=True)
            timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
            screenshot_path = os.path.join("rpa", f"failure_{timestamp}.png")
            page.screenshot(path=screenshot_path, full_page=True)
        except Exception:
            pass
        
        failure_type = "ElementNotFound"
        if isinstance(exc, PlaywrightTimeoutError):
            failure_type = "TimeoutError"
        
        payload = {
            "botId": BOT_ID,
            "page_url": page_url,
            "failure_type": failure_type,
            "failed_action": "update_profile",
            "element_role": "form_field",
            "expected_text": "Update Profile",
            "old_locator": "//button[contains(text(), 'Update Profile')]",
            "old_locator_type": "xpath",
            "error_message": str(exc),
            "page_html": page_html,
            "screenshot_path": screenshot_path,
            "metadata": {
                "bot_id": BOT_ID,
                "bot_service": "dummy_bot",
                "run_id": f"RUN-DUMMY-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            }
        }
        
        response = requests.post(
            f"{ORCHESTRATOR_URL}/report_failure",
            json=payload,
            timeout=10
        )
        print(f"✓ Failure reported: {response.status_code}")
    except Exception as e:
        print(f"✗ Could not report failure: {e}")


def require_locator(page, selector: str):
    locator = page.locator(selector)
    if locator.count() == 0:
        raise Exception(f"Element not found: {selector}")
    return locator


def run():
    """Main bot execution."""
    # Start heartbeat in background
    heartbeat_thread = threading.Thread(target=send_heartbeat, daemon=True)
    heartbeat_thread.start()
    print(f"🔄 Heartbeat thread started")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=800)
        page = browser.new_page()

        page.goto(url)
        page.wait_for_load_state("networkidle")

        try:
            page.locator("text=Settings").click()
            page.wait_for_load_state("networkidle")
            # Use ID-only selectors for the Settings page fields
            full_name = require_locator(page, "#full-name")
            full_name.click()
            full_name.type("John Doe", delay=100)
            page.wait_for_timeout(250)

            role = require_locator(page, "#role")
            role.select_option(label="Risk Analyst")

            work_email = require_locator(page, "#work-email")
            work_email.click()
            work_email.type("john.doe@company.com", delay=100)
            page.wait_for_timeout(250)

            contact_number = require_locator(page, "#contact-number")
            contact_number.click()
            contact_number.type("+1234567890", delay=100)
            page.wait_for_timeout(250)

            # Submit button get by id
            update_profile = require_locator(page, "#update-profile")
            update_profile.click()

            page.wait_for_timeout(5000)

        except Exception as e:
            global bot_running
            bot_running = False  # Stop sending heartbeats
            print(f"❌ Bot execution failed: {e}")
            send_failure_report(page, e)

       


if __name__ == "__main__":
    run()