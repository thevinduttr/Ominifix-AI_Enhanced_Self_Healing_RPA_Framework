"""
scripts.build_dataset

Generate a synthetic training dataset for the reliability model.
Each row represents a single candidate element with its features and label.

To obtain *realistic* performance (e.g. 0.80–0.90 accuracy instead of 1.0),
we deliberately create overlapping feature distributions for positive and
negative samples and add a small amount of label noise.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def generate_dataset(n_positive: int = 4000, n_negative: int = 4000) -> pd.DataFrame:
    rng = np.random.default_rng(seed=42)

    # --------------------------
    # Positive samples (label=1)
    # --------------------------
    # Generally higher similarity, but not perfect and with some spread.
    pos_text_sim = rng.uniform(0.6, 1.0, size=n_positive)   # overlaps with negatives
    pos_id_sim = rng.uniform(0.3, 0.9, size=n_positive)
    pos_name_sim = rng.uniform(0.0, 0.7, size=n_positive)

    pos_heuristic = 0.5 * pos_text_sim + 0.3 * pos_id_sim + 0.2 * pos_name_sim
    pos_label = np.ones(n_positive, dtype=int)

    # --------------------------
    # Negative samples (label=0)
    # --------------------------
    # Lower similarity on average, but still overlapping ranges.
    neg_text_sim = rng.uniform(0.0, 0.8, size=n_negative)
    neg_id_sim = rng.uniform(0.0, 0.6, size=n_negative)
    neg_name_sim = rng.uniform(0.0, 0.6, size=n_negative)

    neg_heuristic = 0.5 * neg_text_sim + 0.3 * neg_id_sim + 0.2 * neg_name_sim
    neg_label = np.zeros(n_negative, dtype=int)

    # Concatenate
    heuristic_score = np.concatenate([pos_heuristic, neg_heuristic])
    text_similarity = np.concatenate([pos_text_sim, neg_text_sim])
    id_similarity = np.concatenate([pos_id_sim, neg_id_sim])
    name_similarity = np.concatenate([pos_name_sim, neg_name_sim])
    labels = np.concatenate([pos_label, neg_label])

    # --------------------------
    # Add label noise (5–10%)
    # --------------------------
    n_samples = labels.shape[0]
    noise_ratio = 0.08  # 8% noisy labels
    n_noisy = int(n_samples * noise_ratio)

    noisy_indices = rng.choice(n_samples, size=n_noisy, replace=False)
    labels[noisy_indices] = 1 - labels[noisy_indices]  # flip 0 <-> 1

    data = {
        "heuristic_score": heuristic_score,
        "text_similarity": text_similarity,
        "id_similarity": id_similarity,
        "name_similarity": name_similarity,
        "label": labels,
    }

    df = pd.DataFrame(data)
    df = df.sample(frac=1.0, random_state=42).reset_index(drop=True)  # shuffle
    return df


def main() -> None:
    target_dir = Path("data/processed")
    target_dir.mkdir(parents=True, exist_ok=True)
    out_path = target_dir / "training_dataset.csv"

    df = generate_dataset()
    df.to_csv(out_path, index=False)
    print(f"Saved synthetic dataset with {len(df)} rows to {out_path}")


if __name__ == "__main__":
    main()
