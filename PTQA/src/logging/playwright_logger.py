import json
import datetime
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright


def append_event(path, event):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def run_and_log(url: str, output_path: str = "logs/playwright.jsonl", headless: bool = True):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context()
        page = ctx.new_page()

        page.on("console", lambda msg: append_event(output_path, {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "session_id": f"pw-{id(page)}",
            "component": "playwright_flow",
            "event_type": "console",
            "selector": None,
            "message": msg.text(),
            "status": "info",
            "meta": {"type": msg.type()}
        }))

        page.on("pageerror", lambda err: append_event(output_path, {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "session_id": f"pw-{id(page)}",
            "component": "playwright_flow",
            "event_type": "pageerror",
            "selector": None,
            "message": str(err),
            "status": "error",
            "meta": {}
        }))

        try:
            append_event(output_path, {
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "session_id": f"pw-{id(page)}",
                "component": "playwright_flow",
                "event_type": "navigation_start",
                "selector": None,
                "message": f"goto {url}",
                "status": "info",
                "meta": {"url": url}
            })
            page.goto(url)
            append_event(output_path, {
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "session_id": f"pw-{id(page)}",
                "component": "playwright_flow",
                "event_type": "navigation_end",
                "selector": None,
                "message": f"loaded {url}",
                "status": "success",
                "meta": {"url": url}
            })

        finally:
            browser.close()


def cli():
    p = argparse.ArgumentParser()
    p.add_argument("url", help="URL to open and log")
    p.add_argument("--out", default="logs/playwright.jsonl", help="Output JSONL path")
    p.add_argument("--headless", action="store_true", help="Run browser headless")
    args = p.parse_args()
    run_and_log(args.url, args.out, headless=args.headless)


if __name__ == "__main__":
    cli()
