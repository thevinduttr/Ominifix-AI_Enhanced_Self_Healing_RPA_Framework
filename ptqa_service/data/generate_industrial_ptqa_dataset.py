"""
Industrial-style PTQA training dataset generator.

This script creates a realistic, imbalanced dataset of healed RPA events
with fields aligned to the PTQA feature pipeline:

FEATURES used by the model:
- model_confidence
- is_success_status
- locator_changed
- is_visual_strategy
- last_n_failures
- avg_exec_time_before
- avg_exec_time_after

LABEL:
- failed  (1 = post-healing is risky/likely to fail, 0 = stable)

Additional metadata columns are included to make the dataset
look and behave more like real industrial logs (bot_id, environment, etc.).
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd


N_ROWS = 10000  # number of industrial-style samples
RANDOM_STATE = 42
OUTPUT_PATH = Path("data/ptqa_training_data.csv")


def _choice(rng: np.random.Generator, items: List[str], probs: List[float]) -> str:
    return rng.choice(items, p=probs)


def generate_industrial_ptqa_dataset(
    n_rows: int = N_ROWS,
    random_state: int = RANDOM_STATE,
) -> pd.DataFrame:
    rng = np.random.default_rng(random_state)

    bot_ids = [f"BOT_{i:03d}" for i in range(1, 31)]  # 30 bots
    environments = ["dev", "qa", "prod"]
    env_probs = [0.2, 0.3, 0.5]  # prod gets more traffic

    # Locator strategies – textual, mapped to is_visual_strategy
    strategies = ["dom", "css", "vision", "ocr", "hybrid"]
    strategy_probs = [0.30, 0.25, 0.20, 0.10, 0.15]

    records = []

    for i in range(n_rows):
        # --- Context-level fields ---
        bot_id = rng.choice(bot_ids)
        environment = _choice(rng, environments, env_probs)
        strategy = _choice(rng, strategies, strategy_probs)

        is_visual_strategy = 1.0 if strategy in ("vision", "ocr", "hybrid") else 0.0

        # Number of recent failures before healing – approx. Poisson
        last_n_failures = int(np.clip(rng.poisson(lam=1.8), 0, 20))

        # Did locator actually change in this healing?
        locator_changed = 1.0 if rng.random() < 0.7 else 0.0

        # Baseline failure risk – we combine several factors
        # Start with a relatively high base risk (industrial reality: many healings are fragile)
        base_risk = 0.35

        # More failures in history -> higher risk
        base_risk += min(last_n_failures * 0.03, 0.30)

        # Production environment tends to be riskier
        if environment == "prod":
            base_risk += 0.10
        elif environment == "qa":
            base_risk += 0.03

        # Visual / OCR strategies can be more fragile
        if is_visual_strategy:
            base_risk += 0.07

        # If locator changed, some extra risk
        if locator_changed:
            base_risk += 0.05

        # Clamp between [0.05, 0.95]
        p_fail_true = float(np.clip(base_risk + rng.normal(0, 0.05), 0.05, 0.95))

        # Draw the ground truth label: 1 = risky / failure, 0 = stable
        failed = int(rng.random() < p_fail_true)

        # We want global imbalance: approx 60–70% failures
        # With the above construction and parameters, it naturally tends that way.

        # --- Execution time modelling (before/after healing) ---
        # Baseline execution time before healing (log-normal-ish)
        base_time = float(np.exp(rng.normal(math.log(1.2), 0.4)))  # around ~1.2s

        if failed:
            # Often slower or unstable after healing
            delta = rng.normal(loc=0.35, scale=0.25)  # positive on average
        else:
            # Sometimes slightly improved, sometimes same, small variance
            delta = rng.normal(loc=0.0, scale=0.12)

        avg_exec_time_before = base_time
        avg_exec_time_after = max(0.1, base_time * (1.0 + delta))

        # --- Model confidence simulation ---
        # Model confidence should be roughly inverse to true failure risk,
        # but with noise to reflect imperfect calibration.
        raw_conf = 1.0 - p_fail_true + rng.normal(0, 0.08)
        model_confidence = float(np.clip(raw_conf, 0.05, 0.99))

        # --- Healing status (immediate result vs final label) ---
        # Some failures may still be reported as "success" immediately
        # but fail later in production.
        if failed:
            # 70% of failed cases show up as immediate failure, 30% look "successful" but are risky.
            is_success_status = 0.0 if rng.random() < 0.7 else 1.0
        else:
            # Almost all stable healings appear as success
            is_success_status = 1.0 if rng.random() < 0.9 else 0.0

        # Old/new locator text – purely for realism (not used as numeric features)
        old_locator = f"//div[@id='old-{rng.integers(100, 999)}']"
        if locator_changed:
            new_locator = f"//div[@id='new-{rng.integers(100, 999)}']"
        else:
            new_locator = old_locator

        healing_id = f"H{2025}{i:05d}"  # example healing id pattern

        record = {
            # --- Business / context fields (not used as features but good for realism) ---
            "healing_id": healing_id,
            "bot_id": bot_id,
            "environment": environment,
            "strategy": strategy,
            "old_locator": old_locator,
            "new_locator": new_locator,
            # --- Core model features ---
            "model_confidence": model_confidence,
            "is_success_status": is_success_status,
            "locator_changed": locator_changed,
            "is_visual_strategy": is_visual_strategy,
            "last_n_failures": float(last_n_failures),
            "avg_exec_time_before": avg_exec_time_before,
            "avg_exec_time_after": avg_exec_time_after,
            # --- Label ---
            "failed": failed,
        }

        records.append(record)

    df = pd.DataFrame.from_records(records)
    return df


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df = generate_industrial_ptqa_dataset()

    # Quick summary
    failed_rate = df["failed"].mean()
    print(f"Generated {len(df)} rows.")
    print(f"Failure ratio (failed=1): {failed_rate:.3f}")

    print("Head:")
    print(df.head())

    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved dataset to {OUTPUT_PATH.resolve()}")


if __name__ == "__main__":
    main()
