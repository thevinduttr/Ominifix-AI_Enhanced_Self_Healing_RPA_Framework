"""Generate small deterministic synthetic Playwright/Selenium JSONL logs with labels for testing.
"""
import json
import datetime
from pathlib import Path
import random


def generate_event(ts, session_id, component, event_type, message, status, label=None):
    return {
        "timestamp": ts.isoformat() + "Z",
        "session_id": session_id,
        "component": component,
        "event_type": event_type,
        "selector": None,
        "message": message,
        "status": status,
        "meta": {},
        "label": label,
    }


def generate_synthetic_logs(out_playwright: str = "logs/playwright_synth.jsonl", out_selenium: str = "logs/selenium_synth.jsonl", n: int = 100, fail_rate: float = 0.1, seed: int = 42):
    Path(out_playwright).parent.mkdir(parents=True, exist_ok=True)
    Path(out_selenium).parent.mkdir(parents=True, exist_ok=True)
    rnd = random.Random(seed)
    now = datetime.datetime.utcnow()

    with open(out_playwright, "w", encoding="utf-8") as pwf, open(out_selenium, "w", encoding="utf-8") as sef:
        for i in range(n):
            ts = now + datetime.timedelta(seconds=i)
            # half playwright, half selenium events
            session_pw = f"pw-sess-{i//2}"
            session_se = f"se-sess-{i//2}"

            # decide if this event is a failure
            is_fail = rnd.random() < fail_rate

            # Playwright event
            pw_event = generate_event(ts, session_pw, "checkout", "pageerror" if is_fail else "console", "timeout waiting for click" if is_fail else "info message", "error" if is_fail else "info", 1 if is_fail else 0)
            pwf.write(json.dumps(pw_event) + "\n")

            # Selenium event
            se_event = generate_event(ts, session_se, "login", "browser_log" if not is_fail else "error", "JS exception" if is_fail else "navigation succeeded", "error" if is_fail else "success", 1 if is_fail else 0)
            sef.write(json.dumps(se_event) + "\n")


if __name__ == "__main__":
    generate_synthetic_logs()
