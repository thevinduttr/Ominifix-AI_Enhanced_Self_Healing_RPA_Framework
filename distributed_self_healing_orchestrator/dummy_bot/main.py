import os
import threading
import time
from datetime import datetime, UTC
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

url = "https://bank-system-for-rp-system.vercel.app/"
BOT_ID = "DUMMY-BOT-new"
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8000")
HEARTBEAT_INTERVAL_SECONDS = 5
bot_running = True  # Flag to control heartbeat


def env_flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes"}


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

        # Use absolute path so healing engine can resolve script without RPA_ROOT.
        script_path = os.path.abspath(__file__)

        # Extract failing line from traceback if possible.
        failing_line = 1
        tb = exc.__traceback__
        while tb:
            if tb.tb_frame.f_code.co_filename == __file__:
                failing_line = tb.tb_lineno
            tb = tb.tb_next

        # Keep old locator aligned with the actual Playwright error string.
        error_text = str(exc)
        old_locator = ""
        if "Element not found:" in error_text:
            old_locator = error_text.split("Element not found:", 1)[1].strip()

        screenshot_path = ""
        try:
            os.makedirs("rpa", exist_ok=True)
            timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
            screenshot_path = os.path.join("rpa", f"failure_{timestamp}.png")
            page.screenshot(path=screenshot_path, full_page=True)
        except Exception:
            pass

        failure_type = "ELEMENT_NOT_FOUND"
        if isinstance(exc, PlaywrightTimeoutError):
            failure_type = "TIMEOUT_ERROR"

        payload = {
            "botId": BOT_ID,
            "page_url": page_url,
            "failure_type": failure_type,
            "failed_action": "locator",
            "element_role": "form_field",
            "expected_text": "Update Profile",
            "old_locator": old_locator,
            "old_locator_type": "css",
            "error_message": error_text,
            "page_html": page_html,
            "screenshot_path": screenshot_path,
            "metadata": {
                "bot_id": BOT_ID,
                "bot_service": "dummy_bot",
                "script_path": script_path,
                "failing_line": failing_line,
                "page_name": "settings",
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
    global bot_running

    # Start heartbeat in background
    heartbeat_thread = threading.Thread(target=send_heartbeat)
    heartbeat_thread.start()
    print(f"🔄 Heartbeat thread started")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=env_flag("HEADLESS"), slow_mo=800)
            page = browser.new_page()

            page.goto(url)
            page.wait_for_load_state("networkidle")

            try:
                username_input = require_locator(page, "input[placeholder='admin']")
                username_input.fill("admin")

                password_input = require_locator(page, "input[placeholder='admin123']")
                password_input.fill("admin123")

                login_button = require_locator(page, "button[type='submit']")
                login_button.click()

                page.wait_for_load_state("networkidle")

                page.locator("text=Settings").click()
                page.wait_for_load_state("networkidle")

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

                update_profile = require_locator(page, "#update-profile")
                update_profile.click()

                page.wait_for_timeout(5000)

            except Exception as e:
                bot_running = False
                print(f"❌ Bot execution failed: {e}")
                send_failure_report(page, e)

            while bot_running:
                time.sleep(1)
    except KeyboardInterrupt:
        print("⛔ Bot stopped by Ctrl+C")
    finally:
        bot_running = False
        heartbeat_thread.join()


if __name__ == "__main__":
    run()
