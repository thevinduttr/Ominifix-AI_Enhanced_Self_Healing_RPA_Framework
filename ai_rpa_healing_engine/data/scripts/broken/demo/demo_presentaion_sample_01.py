from playwright.sync_api import sync_playwright
import time


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto("https://www.sliit.lk/")

        # Step 01 
        page.fill("textarea[name='qqq']", "OpenAI")

        page.keyboard.press("Enter")
        page.wait_for_timeout(2000)

        browser.close()


if __name__ == "__main__":
    run()
