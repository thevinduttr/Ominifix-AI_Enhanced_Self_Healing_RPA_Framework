from __future__ import annotations

from typing import Any, Dict

from bots._pw_utils import run_playwright_flow


def run_main_flow(context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    context = context or {}

    def flow(page):
        page.goto("https://the-internet.herokuapp.com/dynamic_loading/2", wait_until="domcontentloaded")

        page.get_by_text("Start", exact=True).click()

        # Wait for success text
        page.get_by_text("Hello World!", exact=True).wait_for(timeout=12000)

        # Assert visible
        assert page.get_by_text("Hello World!", exact=True).is_visible()

    return run_playwright_flow(context, "dynamic_loading", flow)