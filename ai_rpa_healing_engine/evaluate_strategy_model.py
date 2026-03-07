"""
Strategy Selector Model Evaluation Script

Evaluates the trained strategy_selector_v1 model on test data.
Computes metrics, comparison with baseline, and generates visualizations.

Requirements:
  - Trained model at models/strategy_selector_v1.pkl
  - Dataset at data/ml/healing_dataset.csv

Output:
  - Prints classification report + accuracy
  - Saves confusion matrix to data/results/eval_confusion_matrix.png
  - Saves evaluation results to data/results/eval_results.json
"""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split

# Visualization (optional)
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    HAS_PLOTTING = True
except ImportError:
    HAS_PLOTTING = False
    print("[WARN] matplotlib/seaborn not available - skipping visualization")


# ========================================
# CONFIG
# ========================================
DATASET_PATH = "data/ml/healing_dataset.csv"
MODEL_PATH = "models/strategy_selector_v1.pkl"
RESULTS_DIR = Path("data/results")
LABEL_COLUMN = "strategy"
TEST_SIZE = 0.2
RANDOM_STATE = 42


# ========================================
# LOAD DATA
# ========================================
print("[INFO] Loading dataset...")
df = pd.read_csv(DATASET_PATH)

print(f"[INFO] Dataset size: {df.shape}")
print(f"\n[INFO] Label distribution:")
print(df[LABEL_COLUMN].value_counts())

# Filter to SUCCESS outcomes only (training constraint)
df = df[df["outcome"] == "SUCCESS"].copy()
print(f"\n[INFO] Using SUCCESS cases: {len(df)} records")

# ========================================
# FEATURE ENGINEERING
# (must match train_strategy_model.py logic)
# ========================================
print("[INFO] Engineering features...")

# Combine text fields (fixed column names to match dataset_logger.py header)
text_columns = ["error_type", "old_locator", "element_html"]  # FIX: was "new_element_html"

# Verify columns exist
missing_cols = [c for c in text_columns if c not in df.columns]
if missing_cols:
    raise ValueError(f"Missing columns in dataset: {missing_cols}")

df["combined_text"] = df[text_columns].fillna("").agg(" ".join, axis=1).str.strip()

X = df["combined_text"]
y = df[LABEL_COLUMN]

# ========================================
# TRAIN / TEST SPLIT
# (same split as training for consistency)
# ========================================
print("[INFO] Splitting data...")
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=TEST_SIZE,
    stratify=y,
    random_state=RANDOM_STATE
)

print(f"[INFO] Train size: {len(X_train)}")
print(f"[INFO] Test size: {len(X_test)}")

# ========================================
# LOAD MODEL
# ========================================
print(f"\n[INFO] Loading model from: {MODEL_PATH}")
model = joblib.load(MODEL_PATH)
print(f"[INFO] Model type: {type(model)}")

# ========================================
# BASELINE COMPARISON (ZeroR - majority class)
# ========================================
print("\n[INFO] Computing baseline (ZeroR - majority class)...")
baseline = DummyClassifier(strategy="most_frequent", random_state=RANDOM_STATE)
baseline.fit(X_train, y_train)
y_baseline = baseline.predict(X_test)

baseline_accuracy = accuracy_score(y_test, y_baseline)
baseline_f1 = f1_score(y_test, y_baseline, average="weighted")

print(f"[BASELINE] Accuracy: {baseline_accuracy:.4f}")
print(f"[BASELINE] F1 (weighted): {baseline_f1:.4f}")

# ========================================
# MODEL PREDICTION
# ========================================
print("\n[INFO] Evaluating model...")
y_pred = model.predict(X_test)

# ========================================
# METRICS
# ========================================
accuracy = accuracy_score(y_test, y_pred)
f1_macro = f1_score(y_test, y_pred, average="macro")
f1_weighted = f1_score(y_test, y_pred, average="weighted")

print("\n" + "=" * 60)
print("MODEL EVALUATION RESULTS")
print("=" * 60)
print(f"Test Accuracy:       {accuracy:.4f}  (baseline: {baseline_accuracy:.4f})")
print(f"F1 Score (macro):    {f1_macro:.4f}")
print(f"F1 Score (weighted): {f1_weighted:.4f}  (baseline: {baseline_f1:.4f})")
print(f"Improvement:         {(accuracy - baseline_accuracy):.4f} ({(accuracy - baseline_accuracy) / baseline_accuracy * 100:+.1f}%)")

print("\n" + "-" * 60)
print("CLASSIFICATION REPORT (Per-Class Metrics)")
print("-" * 60)
report_dict = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
print(classification_report(y_test, y_pred, zero_division=0))

# ========================================
# CONFUSION MATRIX
# ========================================
labels = sorted(y_test.unique())
cm = confusion_matrix(y_test, y_pred, labels=labels)

if HAS_PLOTTING:
    print("\n[INFO] Generating confusion matrix visualization...")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    plt.figure(figsize=(8, 6))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=labels,
        yticklabels=labels,
        cbar_kws={"label": "Count"},
    )
    plt.xlabel("Predicted Strategy")
    plt.ylabel("Actual Strategy")
    plt.title("Strategy Selector Confusion Matrix (Evaluation)")
    plt.tight_layout()
    
    cm_path = RESULTS_DIR / "eval_confusion_matrix.png"
    plt.savefig(cm_path, dpi=150)
    print(f"[SAVED] Confusion matrix: {cm_path}")
    plt.close()

# ========================================
# SAVE RESULTS
# ========================================
print("\n[INFO] Saving evaluation results...")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

eval_results = {
    "model_path": MODEL_PATH,
    "dataset_path": DATASET_PATH,
    "test_size": len(X_test),
    "metrics": {
        "accuracy": float(accuracy),
        "f1_macro": float(f1_macro),
        "f1_weighted": float(f1_weighted),
    },
    "baseline": {
        "accuracy": float(baseline_accuracy),
        "f1_weighted": float(baseline_f1),
        "strategy": "most_frequent (ZeroR)",
    },
    "improvement": {
        "accuracy_gain": float(accuracy - baseline_accuracy),
        "accuracy_gain_percent": float((accuracy - baseline_accuracy) / baseline_accuracy * 100),
    },
    "classification_report": report_dict,
    "confusion_matrix": cm.tolist(),
    "labels": labels,
}

results_path = RESULTS_DIR / "eval_results.json"
with open(results_path, "w", encoding="utf-8") as f:
    json.dump(eval_results, f, indent=2)

print(f"[SAVED] Evaluation results: {results_path}")

print("\n" + "=" * 60)
print("EVALUATION COMPLETE")
print("=" * 60)

