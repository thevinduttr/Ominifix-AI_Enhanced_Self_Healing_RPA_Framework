import json
import datetime
from pathlib import Path
import argparse

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


def append_event(path, event):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def run_and_log(url: str, output_path: str = "logs/selenium.jsonl", headless: bool = True):
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")

    # configure logging preferences via options (Selenium 4-compatible)
    chrome_options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        driver.get(url)
        append_event(output_path, {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "session_id": f"se-{id(driver)}",
            "component": "selenium_flow",
            "event_type": "navigation_end",
            "selector": None,
            "message": f"loaded {url}",
            "status": "success",
            "meta": {"url": url}
        })

        entries = driver.get_log("browser")
        for e in entries:
            append_event(output_path, {
                "timestamp": datetime.datetime.utcfromtimestamp(e.get("timestamp", 0) / 1000).isoformat() + "Z",
                "session_id": f"se-{id(driver)}",
                "component": "selenium_flow",
                "event_type": "browser_log",
                "selector": None,
                "message": e.get("message"),
                "status": "info",
                "meta": {"level": e.get("level")}
            })

    finally:
        driver.quit()


def cli():
    p = argparse.ArgumentParser()
    p.add_argument("url", help="URL to open and log")
    p.add_argument("--out", default="logs/selenium.jsonl", help="Output JSONL path")
    p.add_argument("--headless", action="store_true", help="Run browser headless")
    args = p.parse_args()
    run_and_log(args.url, args.out, headless=args.headless)


if __name__ == "__main__":
    cli()
