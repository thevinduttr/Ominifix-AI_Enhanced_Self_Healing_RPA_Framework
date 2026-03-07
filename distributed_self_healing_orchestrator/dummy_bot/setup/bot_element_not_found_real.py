import os
import random
import time
import importlib
from datetime import datetime
from pathlib import Path

import requests

# Realistic bot: fetches a live page, then intentionally fails on a missing selector.
MONITOR_URL = os.environ.get("MONITOR_URL", "http://localhost:8000/heartbeat")
BOT_ID = os.environ.get("BOT_ID", f"BOT-REAL-ELEMENT-{random.randint(4000, 4999)}")
HEARTBEAT_INTERVAL = float(os.environ.get("HEARTBEAT_INTERVAL", "3"))
FAILURE_EVERY = int(os.environ.get("FAILURE_EVERY", "4"))
TARGET_URL = os.environ.get("TARGET_URL", "https://www.wikipedia.org/")
MISSING_SELECTOR = os.environ.get("MISSING_SELECTOR", "#non_existing_checkout_button")
HEADLESS = os.environ.get("HEADLESS", "false").strip().lower() in {"1", "true", "yes"}
WAIT_TIMEOUT_SECONDS = int(os.environ.get("WAIT_TIMEOUT_SECONDS", "8"))
ARTIFACTS_DIR = Path(os.environ.get("ARTIFACTS_DIR", "/app/artifacts"))

REPORT_FAILURE_URL = MONITOR_URL.replace("/heartbeat", "/report_failure")


def _log_step(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def post_heartbeat() -> None:
    payload = {
        "botId": BOT_ID,
        "meta": {
            "instance": "bot_element_not_found_real",
            "target_url": TARGET_URL,
        },
    }
    requests.post(MONITOR_URL, json=payload, timeout=3)


def fetch_live_page_html() -> str:
    try:
        # Use a common browser UA so some sites don't block basic clients.
        response = requests.get(
            TARGET_URL,
            timeout=8,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/121.0.0.0 Safari/537.36"
                )
            },
        )
        return response.text[:120000]
    except Exception as exc:
        # Still send a failure payload if page fetch itself fails.
        return f"<html><body><pre>Failed to fetch page: {exc}</pre></body></html>"


def run_browser_flow() -> tuple[str, str | None, str | None]:
    """
    Returns (page_html, screenshot_path, browser_error_message).
    If browser setup fails, page_html is collected via fallback HTTP fetch.
    """
    try:
        webdriver = importlib.import_module("selenium.webdriver")
        TimeoutException = importlib.import_module("selenium.common.exceptions").TimeoutException
        Options = importlib.import_module("selenium.webdriver.chrome.options").Options
        By = importlib.import_module("selenium.webdriver.common.by").By
        EC = importlib.import_module("selenium.webdriver.support.expected_conditions")
        WebDriverWait = importlib.import_module("selenium.webdriver.support.ui").WebDriverWait
    except Exception:
        return fetch_live_page_html(), None, "Selenium not installed in runtime"

    driver = None
    try:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

        chrome_options = Options()
        if HEADLESS:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1366,768")

        _log_step("Launching browser")
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(TARGET_URL)
        _log_step(f"Opened website: {TARGET_URL}")

        screenshot_file = ARTIFACTS_DIR / f"{BOT_ID}_{int(time.time())}.png"
        driver.save_screenshot(str(screenshot_file))
        _log_step(f"Captured screenshot: {screenshot_file}")

        # Intentionally wait for a selector that does not exist.
        _log_step(f"Searching for selector (expected to fail): {MISSING_SELECTOR}")
        WebDriverWait(driver, WAIT_TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, MISSING_SELECTOR))
        )

        # Should not happen with a missing selector, but keep safe fallback.
        page_html = driver.page_source
        return page_html[:120000], str(screenshot_file), None
    except TimeoutException:
        page_html = driver.page_source[:120000] if driver else fetch_live_page_html()
        return page_html, str(screenshot_file) if 'screenshot_file' in locals() else None, None
    except Exception as exc:
        page_html = driver.page_source[:120000] if driver else fetch_live_page_html()
        return page_html, str(screenshot_file) if 'screenshot_file' in locals() else None, str(exc)
    finally:
        if driver is not None:
            try:
                driver.quit()
                _log_step("Closed browser")
            except Exception:
                pass


def post_element_not_found_failure(cycle: int) -> None:
    run_id = f"RUN-ELEMENT-NOT-FOUND-{cycle:04d}"
    page_html, screenshot_path, browser_error = run_browser_flow()

    error_suffix = f"; browser_error={browser_error}" if browser_error else ""

    failure_payload = {
        "botId": BOT_ID,
        "error": f"ELEMENT_NOT_FOUND: selector '{MISSING_SELECTOR}' not found on page{error_suffix}",
        "last_action": "find_element",
        "failed_action": "find_element",
        "failure_type": "ELEMENT_NOT_FOUND",
        "strategy": "SelectorLookup",
        "priority": "High",
        "page_url": TARGET_URL,
        "element_role": "primary_action",
        "expected_text": "Search",
        "old_locator": MISSING_SELECTOR,
        "old_locator_type": "css",
        "page_html": page_html,
        "screenshot_path": screenshot_path,
        "template_path": None,
        "metadata": {
            "bot_id": BOT_ID,
            "workflow_step": "search",
            "error_type": "ELEMENT_NOT_FOUND",
            "cycle": cycle,
            "source": "dummy_bot_real",
            "run_id": run_id,
            "script_path": "data/scripts/broken/element_lookup.py",
            "failing_line": 42,
            "base_url": TARGET_URL,
            "target_url": TARGET_URL,
            "environment": "docker",
            "headless": HEADLESS,
            "wait_timeout_seconds": WAIT_TIMEOUT_SECONDS,
            "browser_mode": "selenium_chrome",
        },
    }
    requests.post(REPORT_FAILURE_URL, json=failure_payload, timeout=4)


if __name__ == "__main__":
    print(
        f"bot_element_not_found_real starting: BOT_ID={BOT_ID}, MONITOR_URL={MONITOR_URL}, "
        f"TARGET_URL={TARGET_URL}, HEADLESS={HEADLESS}, FAILURE_EVERY={FAILURE_EVERY}, "
        f"HEARTBEAT_INTERVAL={HEARTBEAT_INTERVAL}s"
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
                post_element_not_found_failure(cycle)
                print(f"ELEMENT_NOT_FOUND failure payload sent from {BOT_ID} (cycle={cycle})")
            except Exception as exc:
                print("Failure report error:", exc)

        time.sleep(HEARTBEAT_INTERVAL)
