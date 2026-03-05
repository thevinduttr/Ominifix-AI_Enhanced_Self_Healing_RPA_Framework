from playwright.sync_api import sync_playwright
import time


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto("https://www.google.com")
        time.sleep(1)

        # TC-01: Search box fill — broken name attribute (qqq instead of q)
        page.fill("textarea[name=\"q\"]", "OpenAI self-healing RPA")

        page.keyboard.press("Enter")
        page.wait_for_timeout(2000)

        browser.close()


if __name__ == "__main__":
    run()
