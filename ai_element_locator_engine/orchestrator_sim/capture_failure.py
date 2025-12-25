import json
import traceback
from selenium.common.exceptions import NoSuchElementException
from broken_bot import run_bot
from selenium import webdriver
import time
import os

def capture_failure():
    try:
        run_bot()
    except Exception as e:
        failure = {
            "page_url": "https://example.com",
            "failure_type": "ElementNotFound",
            "failed_action": "click",
            "element_role": "primary_action",
            "expected_text": "Login",
            "old_locator": "//button[@id='login_old']",
            "old_locator_type": "xpath",
            "error_message": str(e)
        }

        os.makedirs("data/failures", exist_ok=True)
        with open("data/failures/failure_001.json", "w") as f:
            json.dump(failure, f, indent=2)

        print("Failure captured")

if __name__ == "__main__":
    capture_failure()
