"""
Advanced RandomForest trainer with hyperparameter tuning via Optuna.
No external dependencies like OpenMP — works reliably on macOS.
"""
import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Any
import argparse

import optuna
from optuna.pruners import MedianPruner
from sklearn.model_selection import GroupKFold, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)


class RFTrainer:
    """Train and evaluate RandomForest for RPA failure prediction."""

    def __init__(self, n_trials: int = 50, cv_splits: int = 5, seed: int = 42):
        """Initialize trainer."""
        self.n_trials = n_trials
        self.cv_splits = cv_splits
        self.seed = seed
        self.model = None
        self.feature_names = None
        self.best_params = None

    def load_data(self, parquet_path: str) -> Tuple[pd.DataFrame, pd.Series, List[str], pd.Series]:
        """Load Parquet file and extract features/labels as DataFrame/Series (with names)."""
        df = pd.read_parquet(parquet_path)
        print(f"Loaded {len(df)} samples from {parquet_path}")

        if "label" in df.columns:
            y = df["label"]
        else:
            raise ValueError("No 'label' column found in data")

        drop_cols = ["label", "timestamp", "session", "component", "type", "selector", "message", "status", "meta"]
        if "features" in df.columns:
            drop_cols.append("features")

        feature_cols = [c for c in df.columns if c not in drop_cols]
        X = df[feature_cols].fillna(0)
        session_ids = df["session"] if "session" in df.columns else pd.Series(np.arange(len(df)), name="session")

        print(f"Features: {len(feature_cols)} dimensions")
        print(f"Label distribution: {y.value_counts().sort_index().to_dict()}")

        return X, y, feature_cols, session_ids

    def objective(self, trial: optuna.Trial, X_train: pd.DataFrame, y_train: pd.Series, groups_train: pd.Series) -> float:
        """Optuna objective using GroupKFold (or StratifiedKFold if only 1 group) cross-validation."""
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 50, 500),
            "max_depth": trial.suggest_int("max_depth", 3, 20),
            "min_samples_split": trial.suggest_int("min_samples_split", 2, 20),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 10),
            "max_features": trial.suggest_categorical("max_features", ["sqrt", "log2"]),
            "class_weight": trial.suggest_categorical("class_weight", [None, "balanced", "balanced_subsample"]),
        }

        cv_scores = []
        n_unique_groups = len(np.unique(groups_train))
        
        # Use StratifiedKFold if only 1 group (e.g., all sessions have same ID)
        if n_unique_groups < 2:
            kfold = StratifiedKFold(n_splits=self.cv_splits, shuffle=True, random_state=self.seed)
            split_gen = kfold.split(X_train, y_train)
        else:
            gkf = GroupKFold(n_splits=min(self.cv_splits, n_unique_groups))
            split_gen = gkf.split(X_train, y_train, groups=groups_train)

        for fold, (train_idx, val_idx) in enumerate(split_gen):
            X_cv_train, X_cv_val = X_train.iloc[train_idx], X_train.iloc[val_idx]
            y_cv_train, y_cv_val = y_train.iloc[train_idx], y_train.iloc[val_idx]

            if len(np.unique(y_cv_train)) == 1 or len(np.unique(y_cv_val)) == 1:
                trial.report(0.5, fold)
                continue

            rf = RandomForestClassifier(**params, random_state=self.seed, n_jobs=-1)
            rf.fit(X_cv_train, y_cv_train)
            y_pred = rf.predict(X_cv_val)

            score = f1_score(y_cv_val, y_pred, zero_division=0)
            cv_scores.append(score)

            trial.report(score, fold)
            if trial.should_prune():
                raise optuna.TrialPruned()

        return np.mean(cv_scores) if cv_scores else 0.5

    def tune_hyperparameters(self, X_train: pd.DataFrame, y_train: pd.Series, groups_train: pd.Series) -> Dict[str, Any]:
        """Tune hyperparameters using Optuna with GroupKFold."""
        print(f"Tuning hyperparameters with Optuna ({self.n_trials} trials)...")

        sampler = optuna.samplers.TPESampler(seed=self.seed)
        pruner = MedianPruner(n_startup_trials=5, n_warmup_steps=2)
        study = optuna.create_study(sampler=sampler, pruner=pruner, direction="maximize")

        study.optimize(
            lambda trial: self.objective(trial, X_train, y_train, groups_train),
            n_trials=self.n_trials,
            show_progress_bar=True,
            catch=(ValueError,),
        )

        best_params = study.best_params
        best_score = study.best_value

        print(f"✓ Best F1 score: {best_score:.4f}")
        print(f"✓ Best parameters: {best_params}")

        self.best_params = best_params
        return best_params

    def train_final_model(self, X_train: pd.DataFrame, y_train: pd.Series, X_val: pd.DataFrame, y_val: pd.Series) -> Dict[str, float]:
        """Train final model and evaluate."""
        if self.best_params is None:
            raise ValueError("Must call tune_hyperparameters() first")

        print("Training final model...")
        self.model = RandomForestClassifier(**self.best_params, random_state=self.seed, n_jobs=-1)
        self.model.fit(X_train, y_train)

        y_pred = self.model.predict(X_val)
        y_pred_proba = self.model.predict_proba(X_val)

        metrics = {
            "accuracy": float(accuracy_score(y_val, y_pred)),
            "precision": float(precision_score(y_val, y_pred, zero_division=0)),
            "recall": float(recall_score(y_val, y_pred, zero_division=0)),
            "f1": float(f1_score(y_val, y_pred, zero_division=0)),
        }

        if len(np.unique(y_val)) > 1:
            metrics["roc_auc"] = float(roc_auc_score(y_val, y_pred_proba[:, 1]))
            cm = confusion_matrix(y_val, y_pred)
            tn, fp, fn, tp = cm.ravel()
            metrics["confusion_matrix"] = {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}
            metrics["specificity"] = float(tn / (tn + fp)) if (tn + fp) > 0 else 0
            metrics["sensitivity"] = float(tp / (tp + fn)) if (tp + fn) > 0 else 0
        else:
            # Single class case
            metrics["confusion_matrix"] = "single_class"
            metrics["specificity"] = 0.0
            metrics["sensitivity"] = 0.0

        print("\nFinal Model Metrics:")
        for key, val in metrics.items():
            if key != "confusion_matrix":
                print(f"  {key}: {val:.4f}")
            else:
                print(f"  {key}: {val}")

        return metrics

    def save_model(self, model_path: str):
        """Save trained model."""
        if self.model is None:
            raise ValueError("No model trained yet")
        joblib.dump(self.model, model_path)
        print(f"✓ Model saved to {model_path}")

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions (probability)."""
        if self.model is None:
            raise ValueError("No model trained yet")
        proba = self.model.predict_proba(X)
        # Handle single-class models
        if proba.shape[1] == 1:
            return np.zeros(len(X))  # All class 0
        return proba[:, 1]


def train_rf_advanced(
    train_parquet: str,
    val_parquet: str,
    model_path: str,
    out_metrics: str,
    out_predictions: str,
    n_trials: int = 50,
    cv_splits: int = 5,
):
    """End-to-end advanced RandomForest training pipeline."""
    trainer = RFTrainer(n_trials=n_trials, cv_splits=cv_splits)

    X_train, y_train, feature_names, groups_train = trainer.load_data(train_parquet)
    X_val, y_val, _, _ = trainer.load_data(val_parquet)

    trainer.feature_names = feature_names

    # Tune hyperparameters
    trainer.tune_hyperparameters(X_train, y_train, groups_train)

    # Train final model
    metrics = trainer.train_final_model(X_train, y_train, X_val, y_val)


    # Save model and metrics
    Path(model_path).parent.mkdir(parents=True, exist_ok=True)
    trainer.save_model(model_path)

    Path(out_metrics).parent.mkdir(parents=True, exist_ok=True)
    with open(out_metrics, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"✓ Metrics saved to {out_metrics}")

    # Save feature names for prediction compatibility
    with open("models/feature_names.json", "w") as f:
        json.dump(feature_names, f)
    print("✓ Feature names saved to models/feature_names.json")

    # Generate predictions
    y_pred_proba = trainer.predict(X_val)
    y_pred_binary = (y_pred_proba > 0.5).astype(int)

    predictions = [
        {"index": i, "true_label": int(y_val[i]), "pred_binary": int(y_pred_binary[i]), "pred_proba": float(y_pred_proba[i])}
        for i in range(len(y_val))
    ]

    Path(out_predictions).parent.mkdir(parents=True, exist_ok=True)
    with open(out_predictions, "w") as f:
        for pred in predictions:
            f.write(json.dumps(pred) + "\n")
    print(f"✓ Predictions saved to {out_predictions}")

    return trainer, metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train advanced RandomForest for RPA failure prediction")
    parser.add_argument("--train", type=str, required=True, help="Training Parquet with features")
    parser.add_argument("--val", type=str, required=True, help="Validation Parquet with features")
    parser.add_argument("--model", type=str, default="models/rf_advanced_model.joblib", help="Output model path")
    parser.add_argument("--out-metrics", type=str, default="output/metrics.json", help="Output metrics JSON")
    parser.add_argument("--out-preds", type=str, default="output/predictions.jsonl", help="Output predictions JSONL")
    parser.add_argument("--n-trials", type=int, default=50, help="Optuna hyperparameter trials")
    parser.add_argument("--cv-splits", type=int, default=5, help="GroupKFold splits")

    args = parser.parse_args()
    train_rf_advanced(args.train, args.val, args.model, args.out_metrics, args.out_preds, args.n_trials, args.cv_splits)
