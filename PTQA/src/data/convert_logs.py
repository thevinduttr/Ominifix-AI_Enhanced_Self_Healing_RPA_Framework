"""
Simple converter to normalize raw JSONL logs into a dataset suitable for training.
Produces `dataset/train.jsonl`, `dataset/val.jsonl`, or Parquet output.
Includes PII scrubbing and heuristic labeling.
"""
import re
import json
import random
import argparse
import glob
from pathlib import Path
from typing import List
import pandas as pd
from typing import List
import pandas as pd


def scrub_pii(text: str) -> str:
    """Mask emails, tokens, phone numbers."""
    if not isinstance(text, str):
        return text
    text = re.sub(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', '<EMAIL>', text)
    text = re.sub(r'\b[A-Za-z0-9]{20,}\b', '<TOKEN>', text)
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '<PHONE>', text)
    return text


def heuristic_label(event: dict) -> int:
    """Auto-label as failure (1) or success (0) based on event content."""
    status = event.get("status", "").lower()
    event_type = event.get("event_type", "").lower()
    message = event.get("message", "").lower()
    
    if status in ("error", "failure"):
        return 1
    if event_type in ("pageerror", "error", "exception"):
        return 1
    if "timeout" in message or "failed" in message or "error" in message:
        return 1
    return 0


def normalize_event(raw: dict) -> dict:
    ev = {
        "timestamp": raw.get("timestamp"),
        "session": raw.get("session_id"),
        "component": raw.get("component", "unknown"),
        "type": raw.get("event_type", "unknown"),
        "selector": raw.get("selector"),
        "message": scrub_pii(raw.get("message", "")),
        "status": raw.get("status", "unknown"),
        "meta": raw.get("meta", {}),
    }
    ev["features"] = {
        "msg_len": len(ev["message"] or ""),
        "is_error": 1 if ev["status"] == "error" or ev["type"] in ("pageerror", "error") else 0,
    }
    ev["label"] = raw.get("label", heuristic_label(raw))
    return ev


def convert(input_paths: List[str], out_train: str = None, out_val: str = None, out_parquet: str = None, val_frac: float = 0.2):
    all_events = []
    for p in input_paths:
        path = Path(p)
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                all_events.append(normalize_event(raw))
            except Exception:
                continue

    # if Parquet output requested, save as DataFrame
    if out_parquet:
        df = pd.DataFrame(all_events)
        # Convert dict columns to strings to avoid Parquet issues with empty structs
        for col in df.columns:
            if df[col].dtype == 'object':
                # Check if column contains dicts
                try:
                    if any(isinstance(v, dict) for v in df[col] if v is not None):
                        df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, dict) else x)
                except:
                    pass
        Path(out_parquet).parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out_parquet, index=False)
        print(f"Saved {len(df)} events to {out_parquet}")
        return

    # otherwise, split and save as JSONL
    random.shuffle(all_events)
    cut = int(len(all_events) * (1 - val_frac))
    train = all_events[:cut]
    val = all_events[cut:]

    Path(out_train).parent.mkdir(parents=True, exist_ok=True)
    Path(out_val).parent.mkdir(parents=True, exist_ok=True)

    with open(out_train, "w", encoding="utf-8") as f:
        for e in train:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    with open(out_val, "w", encoding="utf-8") as f:
        for e in val:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"Saved {len(train)} training + {len(val)} validation events")


def cli():
    p = argparse.ArgumentParser()
    p.add_argument("--inputs", type=str, required=True, help="Glob pattern for input JSONL files")
    p.add_argument("--out-train", default="dataset/train.jsonl")
    p.add_argument("--out-val", default="dataset/val.jsonl")
    p.add_argument("--out-parquet", default=None, help="Output Parquet file (if set, ignore train/val splits)")
    p.add_argument("--val-frac", type=float, default=0.2)
    args = p.parse_args()
    
    import glob
    inputs = glob.glob(args.inputs)
    print(f"Processing {len(inputs)} input files...")
    
    if args.out_parquet:
        convert(inputs, out_parquet=args.out_parquet)
    else:
        convert(inputs, args.out_train, args.out_val, args.val_frac)


if __name__ == "__main__":
    cli()
