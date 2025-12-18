"""
Strategy Selector Model Training Pipeline

Trains a multi-class classifier to predict healing strategies from failure context.
Uses TF-IDF + RandomForest for robust performance on text features.

Output:
  - models/strategy_selector_v1.pkl (trained model)
  - data/results/train_results.json (metrics)
  - data/results/confusion_matrix.png (visualization)
"""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.pipeline import Pipeline

import logging

logger = logging.getLogger(__name__)

# Visualization (optional - handle import gracefully)
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    HAS_PLOTTING = True
except ImportError:
    HAS_PLOTTING = False
    logger.warning("matplotlib/seaborn not available - skipping visualization")


# ========================================
# Configuration
# ========================================
DATASET_PATH = Path("data/ml/healing_dataset.csv")
MODEL_PATH = Path("models/strategy_selector_v1.pkl")
RESULTS_DIR = Path("data/results")
LABEL_COLUMN = "strategy"
TEST_SIZE = 0.2
RANDOM_STATE = 42


def load_dataset() -> pd.DataFrame:
    """Load and validate the healing dataset."""
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH}\n"
            f"Run: python -m src.runner.run_batch_healing to generate dataset"
        )
    
    df = pd.read_csv(DATASET_PATH)
    
    # Validate required columns
    required_cols = ["error_type", "old_locator", "element_html", "strategy", "outcome"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    logger.info("Loaded dataset: %d records", len(df))
    logger.info("Columns: %s", list(df.columns))
    
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Engineer combined text features for TF-IDF."""
    # Combine important text fields (match strategy_predictor.py logic)
    df["combined_text"] = (
        df["error_type"].fillna("") + " " +
        df["old_locator"].fillna("") + " " +
        df["element_html"].fillna("")
    ).str.strip()
    
    return df


def build_candidate_models() -> dict:
    """Create multiple candidate model pipelines for comparison."""
    # Common TF-IDF settings
    tfidf = TfidfVectorizer(
        ngram_range=(1, 2),       # unigrams + bigrams
        max_features=1000,         # limit vocabulary size
        min_df=2,                  # ignore very rare terms
        sublinear_tf=True,         # apply log scaling
    )
    
    # Define candidate classifiers
    classifiers = {
        "RandomForest": RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            class_weight="balanced",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        "LogisticRegression": LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        "SVM": SVC(
            kernel="rbf",
            class_weight="balanced",
            random_state=RANDOM_STATE,
            probability=True,  # Enable probability estimates
        ),
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=RANDOM_STATE,
        ),
    }
    
    # Build pipelines
    models = {}
    for name, classifier in classifiers.items():
        models[name] = Pipeline([
            ("tfidf", tfidf),
            ("classifier", classifier)
        ])
    
    return models


def select_best_model(X_train, y_train) -> tuple:
    """Compare multiple classifiers and select the best one using cross-validation."""
    logger.info("Building candidate model pipelines...")
    models = build_candidate_models()
    
    logger.info("Comparing classifiers with 5-fold cross-validation...")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    
    results = {}
    
    for name, model in models.items():
        logger.info("  - Evaluating %s...", name)
        cv_scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="f1_macro")
        
        results[name] = {
            "mean_f1": cv_scores.mean(),
            "std_f1": cv_scores.std(),
            "scores": cv_scores.tolist()
        }
        
        logger.info("    F1 (macro): %.4f ± %.4f", cv_scores.mean(), cv_scores.std())
    
    # Select best model based on mean F1 score
    best_name = max(results.keys(), key=lambda k: results[k]["mean_f1"])
    best_model = models[best_name]
    
    logger.info("Best classifier: %s (F1: %.4f)", best_name, results[best_name]["mean_f1"])
    
    # Train the best model on full training set
    logger.info("Training best model on full training set...")
    best_model.fit(X_train, y_train)
    
    return best_model, best_name, results


def evaluate_model(model, X_test, y_test):
    """Evaluate model and return metrics."""
    logger.info("Evaluating model on test set...")
    
    y_pred = model.predict(X_test)
    
    # Compute metrics
    accuracy = accuracy_score(y_test, y_pred)
    f1_macro = f1_score(y_test, y_pred, average="macro")
    f1_weighted = f1_score(y_test, y_pred, average="weighted")
    
    # Classification report (per-class metrics)
    report = classification_report(y_test, y_pred, output_dict=True)
    
    # Confusion matrix
    labels = sorted(y_test.unique())
    cm = confusion_matrix(y_test, y_pred, labels=labels)
    
    logger.info("Test Accuracy: %.4f", accuracy)
    logger.info("F1 Score (macro): %.4f", f1_macro)
    logger.info("F1 Score (weighted): %.4f", f1_weighted)
    
    return {
        "accuracy": float(accuracy),
        "f1_macro": float(f1_macro),
        "f1_weighted": float(f1_weighted),
        "classification_report": report,
        "confusion_matrix": cm.tolist(),
        "labels": labels,
    }


def save_confusion_matrix(cm, labels):
    """Save confusion matrix visualization."""
    if not HAS_PLOTTING:
        logger.warning("Confusion matrix visualization (matplotlib not available)")
        return
    
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
    plt.title("Strategy Selector Confusion Matrix")
    plt.tight_layout()
    
    output_path = RESULTS_DIR / "confusion_matrix.png"
    plt.savefig(output_path, dpi=150)
    logger.info("Confusion matrix: %s", output_path)
    plt.close()


def save_results(metrics, train_size, test_size, best_classifier, cv_results):
    """Save training results to JSON."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    output = {
        "model_version": "strategy_selector_v1",
        "dataset_path": str(DATASET_PATH),
        "train_size": train_size,
        "test_size": test_size,
        "test_split": TEST_SIZE,
        "random_state": RANDOM_STATE,
        "best_classifier": best_classifier,
        "cross_validation_results": cv_results,
        "final_test_metrics": metrics,
    }
    
    output_path = RESULTS_DIR / "train_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    
    logger.info("Training results: %s", output_path)


def main():
    """Main training pipeline."""
    logger.info("=" * 60)
    logger.info("STRATEGY SELECTOR MODEL TRAINING")
    logger.info("=" * 60)
    
    # 1. Load dataset
    df = load_dataset()
    
    # 2. Filter to successful outcomes only (labels must match actual healing strategy)
    df_train = df[df["outcome"] == "SUCCESS"].copy()
    logger.info("Training on SUCCESS cases: %d records", len(df_train))
    
    # 3. Check label distribution
    logger.info("Label distribution:")
    logger.info("%s", df_train[LABEL_COLUMN].value_counts())
    
    # 4. Engineer features
    df_train = engineer_features(df_train)
    
    # 5. Split data
    X = df_train["combined_text"]
    y = df_train[LABEL_COLUMN]
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=TEST_SIZE,
        stratify=y,
        random_state=RANDOM_STATE
    )
    
    logger.info("Train size: %d", len(X_train))
    logger.info("Test size: %d", len(X_test))
    
    # 6. Select and train best model
    model, best_classifier, cv_results = select_best_model(X_train, y_train)
    
    # 7. Evaluate on test set
    metrics = evaluate_model(model, X_test, y_test)
    
    # 8. Save model
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    logger.info("Model: %s", MODEL_PATH)
    
    # 9. Save confusion matrix visualization
    cm = np.array(metrics["confusion_matrix"])
    labels = metrics["labels"]
    save_confusion_matrix(cm, labels)
    
    # 10. Save results JSON
    save_results(metrics, len(X_train), len(X_test), best_classifier, cv_results)
    
    logger.info("=" * 60)
    logger.info("TRAINING COMPLETE")
    logger.info("=" * 60)
    logger.info("Best Classifier: %s", best_classifier)
    logger.info("Model saved to: %s", MODEL_PATH)
    logger.info("Results saved to: %s", RESULTS_DIR)
    logger.info("Test Accuracy: %.4f", metrics["accuracy"])
    logger.info("Test F1 (macro): %.4f", metrics["f1_macro"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()

