from __future__ import annotations

from typing import Any, Dict

from bots._pw_utils import run_playwright_flow


def run_main_flow(context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    context = context or {}

    def flow(page):
        page.goto("https://opensource-demo.orangehrmlive.com/", wait_until="domcontentloaded")

        # Intentionally wrong password to simulate broken baseline
        page.locator("input[name='username']").wait_for(state="visible", timeout=15000)
        page.fill("input[name='username']", "Admin")
        page.fill("input[name='password']", "wrong-password")
        page.click("button[type='submit']")

        # Expect dashboard (will fail)
        page.wait_for_timeout(1500)
        assert "dashboard" in page.url.lower(), f"Expected dashboard but got: {page.url}"

    return run_playwright_flow(context, "orangehrm_original_fail", flow)