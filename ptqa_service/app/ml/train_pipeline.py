import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

from app.ml.features import FEATURE_NAMES

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "ptqa_failure_model.joblib"


def load_training_data(csv_path: str) -> tuple[np.ndarray, np.ndarray]:
    df = pd.read_csv(csv_path)

    # X = features, y = label
    X = df[FEATURE_NAMES].to_numpy(dtype=float)
    y = df["failed"].to_numpy(dtype=int)
    return X, y


def train_and_save(csv_path: str) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    X, y = load_training_data(csv_path)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # --- Base models ---
    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced",
    )

    gb = GradientBoostingClassifier(
        n_estimators=150,
        learning_rate=0.05,
        max_depth=3,
        random_state=42,
    )

    # --- Soft-voting ensemble: RandomForest + GradientBoosting ---
    clf = VotingClassifier(
        estimators=[
            ("rf", rf),
            ("gb", gb),
        ],
        voting="soft",          # use predicted probabilities
        weights=[0.6, 0.4],     # slightly favour RF (robust on noisy data)
        n_jobs=-1,
    )

     # Custom label will be persisted by joblib
    clf.model_label = "RandomForest + GradientBoosting (soft-voting ensemble)"

    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print("Base models in ensemble: RandomForestClassifier + GradientBoostingClassifier")
    print(f"Validation accuracy (ensemble): {acc:.3f}")
    print(classification_report(y_test, y_pred))

    joblib.dump(clf, MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")


if __name__ == "__main__":
    csv_path = os.getenv("PTQA_TRAIN_CSV", "data/ptqa_training_data.csv")
    train_and_save(csv_path)
