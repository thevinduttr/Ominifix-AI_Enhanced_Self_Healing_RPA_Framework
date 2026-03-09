from __future__ import annotations

from typing import Any, Dict

from bots._pw_utils import run_playwright_flow


def run_main_flow(context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    ORIGINAL (broken) bot — uses old locator text 'More information...'
    which no longer exists on example.com (now says 'Learn more').
    This simulates a stale locator that needs healing.
    """
    context = context or {}

    def flow(page):
        page.goto("https://example.com", wait_until="domcontentloaded")
        title = page.title()
        assert "Example Domain" in title, f"Unexpected title: {title}"

        # OLD broken locator — text no longer exists on the page
        page.get_by_text("More information...", exact=True).click()
        page.wait_for_timeout(500)
        assert "iana.org" in page.url.lower(), f"Unexpected URL: {page.url}"

    return run_playwright_flow(context, "login_original", flow)
