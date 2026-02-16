from __future__ import annotations

from typing import Any, Dict

from bots._pw_utils import run_playwright_flow


def run_main_flow(context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    context = context or {}

    def flow(page):
        page.goto("https://the-internet.herokuapp.com/add_remove_elements/", wait_until="domcontentloaded")
        page.get_by_text("Add Element", exact=True).click()
        delete_btn = page.locator("button.added-manually")
        delete_btn.wait_for(state="visible", timeout=8000)
        assert delete_btn.count() >= 1

    return run_playwright_flow(context, "add_remove_original", flow)