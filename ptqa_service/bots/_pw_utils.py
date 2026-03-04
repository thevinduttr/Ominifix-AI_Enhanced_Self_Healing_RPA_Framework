from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

from playwright.sync_api import sync_playwright


def run_playwright_flow(
    context: Dict[str, Any],
    test_name: str,
    flow_fn,
) -> Dict[str, Any]:
    """
    Runs a Playwright flow with stable defaults.
    - context["headless"]: bool
    - context["record_video"]: bool
    Returns: {"success": bool, "video_path": str|None}
    """
    headless = bool((context or {}).get("headless", True))
    record_video = bool((context or {}).get("record_video", False))

    video_path = None

    # Video directory
    videos_dir = Path("artifacts") / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)

        context_args = {}
        if record_video:
            context_args["record_video_dir"] = str(videos_dir)
            context_args["record_video_size"] = {"width": 1280, "height": 720}

        pw_context = browser.new_context(**context_args)
        page = pw_context.new_page()

        # Fast, reliable timeouts
        page.set_default_timeout(8000)
        page.set_default_navigation_timeout(15000)

        try:
            flow_fn(page)

            # Close to finalize video writing
            pw_context.close()
            browser.close()

            # Try to locate a recorded video file (best-effort)
            if record_video:
                # Playwright creates a video per page; path is available before closing in newer versions
                # But to keep it simple, we return None if not found deterministically.
                # Your PTQA still works even without video path.
                pass

            return {"success": True, "video_path": video_path}

        except Exception:
            try:
                pw_context.close()
            except Exception:
                pass
            try:
                browser.close()
            except Exception:
                pass
            return {"success": False, "video_path": video_path}