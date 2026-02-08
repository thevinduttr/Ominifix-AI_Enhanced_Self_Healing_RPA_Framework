from playwright.sync_api import sync_playwright
import time


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto("https://www.google.com")

        time.sleep(2)

        # Search box (this is the locator we will break later)
        page.fill("textarea[name='q_BROKEN_20260305']", "OpenAI")

        page.keyboard.press("Enter")
        page.wait_for_timeout(2000)

        browser.close()


if __name__ == "__main__":
    run()