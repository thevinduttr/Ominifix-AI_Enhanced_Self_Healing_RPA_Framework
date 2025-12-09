#!/usr/bin/env python3
"""
Generate synthetic RPA execution logs for model training with realistic variations.
- Produces JSONL files compatible with src/data/convert_logs.py
- Injects configurable failure rate with varied failure types/messages
- Adds complexity: typos, message variations, selector mutations, timing patterns
- Keeps schema: timestamp, session, component, type, selector, message, status, meta, label
"""
import argparse
import json
import random
import string
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

# Reproducible defaults
random.seed(42)

# Event templates
EVENT_TYPES = [
    "navigation",
    "click",
    "input",
    "console_error",
    "network_request",
    "assertion",
    "wait",
    "screenshot",
    "script_execution",
]

SELECTORS = [
    "#login-btn",
    "#submit",
    "input[name='q']",
    "#search",
    "#cart",
    "#checkout",
    "#username",
    "#password",
    "#otp",
    "#continue",
    "#confirm",
    "#logout",
    "#profile",
    "button.primary",
    "div.modal-content",
    "input[type='email']",
    "form#auth-form",
    "span.error-msg",
]

SUCCESS_MESSAGES = [
    "Clicked element successfully",
    "Input text completed",
    "Navigation completed",
    "HTTP 200 OK",
    "Assertion validation passed",
    "Element located",
    "Page loaded",
    "Form submitted",
    "Data retrieved",
]

FAILURE_MESSAGES = [
    "Timeout waiting for selector",
    "Element not found in DOM",
    "HTTP 500 Internal Server Error",
    "Assertion failed: text mismatch",
    "Navigation error: 404 Not Found",
    "Stale element reference",
    "Connection timeout occurred",
    "Invalid selector expression",
    "Element not clickable",
    "JavaScript error in console",
    "Network request failed",
    "Session expired",
    "Permission denied",
    "Resource unavailable",
    "Rate limit exceeded",
]

FAILURE_TYPES = [
    "timeout",
    "not_found",
    "http_5xx",
    "assertion_failed",
    "http_4xx",
    "stale_element",
    "network_error",
    "invalid_selector",
    "not_clickable",
    "js_error",
]

COMPONENTS = ["playwright", "selenium", "puppeteer", "cypress"]


def introduce_typo(text: str) -> str:
    """Randomly introduce typos (10% chance)."""
    if random.random() > 0.9 and len(text) > 3:
        idx = random.randint(0, len(text) - 1)
        char = random.choice(string.ascii_lowercase)
        return text[:idx] + char + text[idx+1:]
    return text


def introduce_case_variation(text: str) -> str:
    """Randomly vary case (20% chance)."""
    if random.random() < 0.2:
        return text.upper()
    if random.random() < 0.1:
        return text.lower()
    return text


def random_timestamp(start: datetime) -> str:
    # Add up to 15 minutes of jitter for realistic timing
    jitter = timedelta(seconds=random.randint(0, 900))
    return (start + jitter).isoformat() + "Z"


def random_selector() -> str:
    base = random.choice(SELECTORS)
    # Add variations: suffix, attribute mutations, etc. (40% chance)
    if random.random() < 0.4:
        variation_type = random.choice(["suffix", "index", "attribute"])
        if variation_type == "suffix":
            suffix = "-" + "".join(random.choices(string.ascii_lowercase + string.digits, k=2))
            return base + suffix
        elif variation_type == "index":
            return base + f":nth-of-type({random.randint(1, 5)})"
        else:  # attribute
            return base + f"[data-testid='item-{random.randint(100, 999)}']"
    return base


def make_event(session_id: str, base_time: datetime, is_failure: bool) -> Dict:
    etype = random.choice(EVENT_TYPES)
    selector = random_selector()
    component = random.choice(COMPONENTS)
    
    if is_failure:
        msg = random.choice(FAILURE_MESSAGES)
        # Add variations to failure message
        msg = introduce_typo(msg)
        msg = introduce_case_variation(msg)
        status = "ERROR"
        failure_kind = random.choice(FAILURE_TYPES)
        http_status = random.choice([400, 401, 403, 404, 408, 429, 500, 502, 503])
        label = 1
    else:
        msg = random.choice(SUCCESS_MESSAGES)
        # Add variations to success message
        msg = introduce_typo(msg)
        msg = introduce_case_variation(msg)
        status = random.choice(["SUCCESS", "OK"]) if random.random() > 0.05 else "PARTIAL"
        failure_kind = None
        http_status = random.choice([200, 201, 204])
        label = 0

    meta = {
        "url": f"https://app.example.com/path/{random.randint(1, 20)}",
        "http_status": http_status,
        "failure_kind": failure_kind,
    }

    return {
        "timestamp": random_timestamp(base_time),
        "session": session_id,
        "component": component,
        "type": etype,
        "selector": selector,
        "message": msg,
        "status": status,
        "meta": meta,
        # Label: 1 = failure, 0 = success
        "label": label,
    }


def generate_logs(num_events: int, failure_rate: float, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)

    events: List[Dict] = []
    # Roughly 5-12 events per session
    session_size = random.randint(5, 12)
    current_session_events = 0
    session_id = f"sess-{uuid.uuid4().hex[:8]}"
    base_time = datetime.utcnow()

    for _ in range(num_events):
        # Start a new session when current one is big enough
        if current_session_events >= session_size:
            session_id = f"sess-{uuid.uuid4().hex[:8]}"
            current_session_events = 0
            session_size = random.randint(5, 12)
            base_time = datetime.utcnow()

        is_failure = random.random() < failure_rate
        event = make_event(session_id, base_time, is_failure)
        events.append(event)
        current_session_events += 1

    with out_path.open("w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")
    print(f"Generated {len(events)} events → {out_path}")


def parse_args():
    parser = argparse.ArgumentParser(description="Generate synthetic JSONL logs for PTQAF")
    parser.add_argument("--count", type=int, default=1000, help="Number of events to generate")
    parser.add_argument("--failure-rate", type=float, default=0.3, help="Failure rate between 0 and 1")
    parser.add_argument("--out", type=str, default="logs/synthetic/synthetic_1000.jsonl", help="Output JSONL path")
    return parser.parse_args()


def main():
    args = parse_args()
    if not (0.0 <= args.failure_rate <= 1.0):
        raise ValueError("failure-rate must be between 0 and 1")
    generate_logs(args.count, args.failure_rate, Path(args.out))


if __name__ == "__main__":
    main()
