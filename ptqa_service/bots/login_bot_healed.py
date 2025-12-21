"""
Real browser-based healed bot using Playwright.

This simulates a healed RPA script by:
- launching a headless Chromium browser
- navigating to https://example.com (public test site)
- verifying that the page title contains "Example Domain"
- closing the browser

PTQA executes this via run_main_flow() during regression tests.
"""

from playwright.sync_api import sync_playwright


def run_main_flow():
    """
    Main RPA flow executed by PTQA regression tests.

    Returns True on success, raises AssertionError/Exception on failure.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to a public demo site
        page.goto("https://example.com", wait_until="networkidle")

        # Simple validation: title should contain "Example Domain"
        title = page.title()
        assert "Example Domain" in title, f"Unexpected page title: {title}"

        page.click("text=More information")

        # Ensure navigation happened
        assert "iana.org" in page.url.lower(), f"Unexpected URL after click: {page.url}"

        browser.close()

        # RPA flow is considered successful
        return True
