import os
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

DATA_HTML_DIR = os.path.join("data", "html")
DATA_SCREENSHOT_DIR = os.path.join("data", "screenshots")

os.makedirs(DATA_HTML_DIR, exist_ok=True)
os.makedirs(DATA_SCREENSHOT_DIR, exist_ok=True)


def run_bot_and_capture_failure():
    page_path = os.path.abspath(os.path.join("demo_pages", "login_v2_changed.html"))
    page_url = "file:///" + page_path.replace("\\", "/")

    driver = webdriver.Chrome()
    driver.get(page_url)
    time.sleep(1)

    failure_context = {
      "page_url": page_url,
      "failure_type": "ElementNotFound",
      "failed_action": "click",
      "element_role": "primary_action",  # login submit / primary button
      "expected_text": "Login",         # what old bot thought
      "html_snapshot_path": None,
      "screenshot_path": None,
      "metadata": {
        "bot_id": "RPA-0012",
        "workflow_step": "login_submit"
      }
    }

    old_locator = "//button[@id='submit-btn']"

    try:
        btn = driver.find_element(By.XPATH, old_locator)
        btn.click()
        print("[!] Bot unexpectedly succeeded (for v1).")
    except NoSuchElementException:
        print("[+] Bot failed to find element – orchestrator will report failure.")

        # Save HTML snapshot
        html = driver.page_source
        html_path = os.path.join(DATA_HTML_DIR, "login_v2_snapshot.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        failure_context["html_snapshot_path"] = html_path

        # Save screenshot
        screenshot_path = os.path.join(DATA_SCREENSHOT_DIR, "login_v2.png")
        driver.save_screenshot(screenshot_path)
        failure_context["screenshot_path"] = screenshot_path

    driver.quit()

    out_path = os.path.join("data", "failure_context.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(failure_context, f, indent=2)

    print("[+] Failure context saved to", out_path)
    return failure_context


if __name__ == "__main__":
    ctx = run_bot_and_capture_failure()
    print(json.dumps(ctx, indent=2))
