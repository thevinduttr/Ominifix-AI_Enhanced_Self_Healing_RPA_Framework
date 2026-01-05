from playwright.sync_api import sync_playwright


def run_main_flow():
    """
    Demo 3:
    Demonstrates handling of dynamic content and waits.
    """

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://the-internet.herokuapp.com/dynamic_loading/2", wait_until="networkidle")

        # Start loading
        page.click("text=Start")

        # Wait for content to appear
        page.wait_for_selector("text=Hello World!", timeout=10000)

        browser.close()
        return True
