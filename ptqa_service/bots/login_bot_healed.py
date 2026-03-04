from __future__ import annotations

from typing import Any, Dict

from bots._pw_utils import run_playwright_flow


def run_main_flow(context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    context = context or {}

    def flow(page):
        page.goto("https://example.com", wait_until="domcontentloaded")
        title = page.title()
        assert "Example Domain" in title, f"Unexpected title: {title}"

        page.get_by_text("More information", exact=False).click()
        page.wait_for_timeout(500)
        assert "iana.org" in page.url.lower(), f"Unexpected URL: {page.url}"

