"""
scripts.train_reliability

Train a RandomForestClassifier as the reliability model using the synthetic
training dataset created by build_dataset.py, then save it to
data/models/reliability_model.pkl.

This script is independent from the API; it is run offline during the
"data preparation / model training" phase of the research.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split


def main() -> None:
    data_path = Path("data/processed/training_dataset.csv")
    if not data_path.exists():
        raise FileNotFoundError(
            f"{data_path} does not exist. Run scripts/build_dataset.py first."
        )

    df = pd.read_csv(data_path)

    feature_cols = ["heuristic_score", "text_similarity", "id_similarity", "name_similarity"]
    X = df[feature_cols].values.astype(float)
    y = df["label"].values.astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced_subsample",
    )

    model.fit(X_train, y_train)

    # Basic evaluation metrics
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_proba)

    print(f"Test Accuracy: {acc:.4f}")
    print(f"Test ROC-AUC : {auc:.4f}")

    # Save model
    target_dir = Path("data/models")
    target_dir.mkdir(parents=True, exist_ok=True)
    out_path = target_dir / "reliability_model.pkl"

    joblib.dump(model, out_path)
    print(f"Saved trained reliability model to {out_path}")


if __name__ == "__main__":
    main()
