from __future__ import annotations

from typing import Any, Dict

from bots._pw_utils import run_playwright_flow


def run_main_flow(context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    context = context or {}

    def flow(page):
        page.goto("https://opensource-demo.orangehrmlive.com/", wait_until="domcontentloaded")

        # Wait for login form
        page.locator("input[name='username']").wait_for(state="visible", timeout=15000)
        page.fill("input[name='username']", "Admin")
        page.fill("input[name='password']", "admin123")
        page.click("button[type='submit']")

        # OrangeHRM sometimes redirects slowly; wait for dashboard-ish URL or menu
        page.wait_for_timeout(1200)
        # Prefer a UI element check instead of URL-only
        page.locator("header").wait_for(state="visible", timeout=15000)

        # Soft check: either dashboard URL OR presence of side panel
        ok_url = "dashboard" in page.url.lower()
        ok_ui = page.locator("aside").count() > 0
        assert (ok_url or ok_ui), f"Login may have failed or page structure changed. URL: {page.url}"

    return run_playwright_flow(context, "orangehrm_login", flow)