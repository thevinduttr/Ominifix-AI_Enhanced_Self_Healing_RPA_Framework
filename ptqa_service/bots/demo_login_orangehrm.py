from playwright.sync_api import sync_playwright


def run_main_flow():
    """
    Demo 2:
    Real login flow to public OrangeHRM demo.
    """

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://opensource-demo.orangehrmlive.com/", wait_until="networkidle")

        page.fill("input[name='username']", "Admin")
        page.fill("input[name='password']", "admin123")

        page.click("button[type='submit']")

        assert "dashboard" in page.url.lower(), f"Login failed: {page.url}"

        browser.close()
        return True
