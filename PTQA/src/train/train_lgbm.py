"""
Advanced LightGBM trainer with hyperparameter tuning via Optuna and GroupKFold evaluation.
Produces better generalization on real RPA failure prediction tasks.
"""
import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime
import argparse

import lightgbm as lgb
import optuna
from optuna.pruners import MedianPruner
from sklearn.model_selection import GroupKFold, StratifiedKFold
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
)


class LGBMTrainer:
    """Train and evaluate LightGBM for RPA failure prediction."""

    def __init__(self, n_trials: int = 50, cv_splits: int = 5, seed: int = 42):
        """
        Initialize trainer.
        Args:
            n_trials: Number of Optuna trials for hyperparameter tuning
            cv_splits: Number of cross-validation folds (preferably GroupKFold by session)
            seed: Random seed for reproducibility
        """
        self.n_trials = n_trials
        self.cv_splits = cv_splits
        self.seed = seed
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = None
        self.best_params = None
        self.cv_scores = {}

    def load_data(self, parquet_path: str) -> Tuple[np.ndarray, np.ndarray, List[str], np.ndarray]:
        """
        Load Parquet file and extract features/labels.
        Args:
            parquet_path: Path to Parquet with features
        Returns:
            X: feature array, y: label array, feature_names: list of feature names, session_ids: array
        """
        df = pd.read_parquet(parquet_path)
        print(f"Loaded {len(df)} samples from {parquet_path}")

        # Identify label column
        if "label" in df.columns:
            y = df["label"].values
        else:
            raise ValueError("No 'label' column found in data")

        # Identify non-feature columns
        drop_cols = ["label", "timestamp", "session", "component", "type", "selector", "message", "status", "meta"]
        if "features" in df.columns:
            drop_cols.append("features")

        # Collect feature columns
        feature_cols = [c for c in df.columns if c not in drop_cols]
        X = df[feature_cols].fillna(0).values
        session_ids = df.get("session", np.arange(len(df))).values

        print(f"Features: {len(feature_cols)} dimensions")
        print(f"Label distribution: {np.bincount(y.astype(int))}")

        return X, y, feature_cols, session_ids

    def objective(self, trial: optuna.Trial, X_train: np.ndarray, y_train: np.ndarray, groups_train: np.ndarray) -> float:
        """
        Optuna objective function for hyperparameter tuning.
        Evaluates a configuration using GroupKFold cross-validation.
        """
        params = {
            "objective": "binary",
            "metric": "binary_logloss",
            "verbosity": -1,
            "seed": self.seed,
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 20, 150),
            "max_depth": trial.suggest_int("max_depth", 3, 15),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 50),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 0.0, 10.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 0.0, 10.0, log=True),
        }

        cv_scores = []
        gkf = GroupKFold(n_splits=self.cv_splits)

        for fold, (train_idx, val_idx) in enumerate(gkf.split(X_train, y_train, groups=groups_train)):
            X_cv_train, X_cv_val = X_train[train_idx], X_train[val_idx]
            y_cv_train, y_cv_val = y_train[train_idx], y_train[val_idx]

            # Handle class imbalance
            if len(np.unique(y_cv_train)) == 1:
                trial.report(0.5, fold)
                continue

            train_data = lgb.Dataset(X_cv_train, label=y_cv_train, free_raw_data=False)
            valid_data = lgb.Dataset(X_cv_val, label=y_cv_val, reference=train_data, free_raw_data=False)

            model = lgb.train(
                params,
                train_data,
                num_boost_round=200,
                valid_sets=[valid_data],
                valid_names=["valid"],
                callbacks=[
                    lgb.early_stopping(stopping_rounds=30, verbose=False),
                    lgb.log_evaluation(period=0),
                ],
            )

            y_pred = model.predict(X_cv_val, num_iteration=model.best_iteration)
            y_pred_binary = (y_pred > 0.5).astype(int)

            # Compute F1 as primary metric (balances precision and recall)
            score = f1_score(y_cv_val, y_pred_binary, zero_division=0)
            cv_scores.append(score)

            trial.report(score, fold)
            if trial.should_prune():
                raise optuna.TrialPruned()

        return np.mean(cv_scores)

    def tune_hyperparameters(
        self, X_train: np.ndarray, y_train: np.ndarray, groups_train: np.ndarray
    ) -> Dict[str, Any]:
        """
        Tune hyperparameters using Optuna with GroupKFold.
        Args:
            X_train: Training features
            y_train: Training labels
            groups_train: Group IDs (e.g., session IDs) for GroupKFold
        Returns:
            Best hyperparameters dictionary
        """
        print(f"Tuning hyperparameters with Optuna ({self.n_trials} trials)...")

        sampler = optuna.samplers.TPESampler(seed=self.seed)
        pruner = MedianPruner(n_startup_trials=10, n_warmup_steps=3)
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

    def train_final_model(
        self, X_train: np.ndarray, y_train: np.ndarray, X_val: np.ndarray, y_val: np.ndarray
    ) -> Dict[str, float]:
        """
        Train final model on full training set using best hyperparameters.
        Evaluate on validation set.
        Returns metrics dictionary.
        """
        if self.best_params is None:
            raise ValueError("Must call tune_hyperparameters() first")

        print("Training final model...")
        params = {
            "objective": "binary",
            "metric": "binary_logloss",
            "verbosity": -1,
            "seed": self.seed,
            **self.best_params,
        }

        train_data = lgb.Dataset(X_train, label=y_train)
        valid_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

        self.model = lgb.train(
            params,
            train_data,
            num_boost_round=500,
            valid_sets=[valid_data],
            valid_names=["valid"],
            callbacks=[
                lgb.early_stopping(stopping_rounds=50, verbose=False),
                lgb.log_evaluation(period=50),
            ],
        )

        # Evaluate
        y_pred = self.model.predict(X_val, num_iteration=self.model.best_iteration)
        y_pred_binary = (y_pred > 0.5).astype(int)

        metrics = {
            "accuracy": accuracy_score(y_val, y_pred_binary),
            "precision": precision_score(y_val, y_pred_binary, zero_division=0),
            "recall": recall_score(y_val, y_pred_binary, zero_division=0),
            "f1": f1_score(y_val, y_pred_binary, zero_division=0),
        }

        # Add ROC-AUC if there are both classes
        if len(np.unique(y_val)) > 1:
            metrics["roc_auc"] = roc_auc_score(y_val, y_pred)

        # Confusion matrix
        tn, fp, fn, tp = confusion_matrix(y_val, y_pred_binary).ravel()
        metrics["confusion_matrix"] = {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}
        metrics["specificity"] = tn / (tn + fp) if (tn + fp) > 0 else 0
        metrics["sensitivity"] = tp / (tp + fn) if (tp + fn) > 0 else 0

        print("\nFinal Model Metrics:")
        for key, val in metrics.items():
            if key != "confusion_matrix":
                print(f"  {key}: {val:.4f}")
            else:
                print(f"  {key}: {val}")

        return metrics

    def save_model(self, model_path: str):
        """Save trained model to disk."""
        if self.model is None:
            raise ValueError("No model trained yet")
        self.model.save_model(model_path, num_iteration=self.model.best_iteration)
        print(f"✓ Model saved to {model_path}")

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions on new data."""
        if self.model is None:
            raise ValueError("No model trained yet")
        return self.model.predict(X)


def train_lgbm_model(
    train_parquet: str,
    val_parquet: str,
    model_path: str,
    out_metrics: str,
    out_predictions: str,
    n_trials: int = 50,
    cv_splits: int = 5,
):
    """
    End-to-end training pipeline: load data, tune hyperparameters, train, evaluate, save.
    Args:
        train_parquet: Path to training Parquet with features
        val_parquet: Path to validation Parquet with features
        model_path: Where to save the trained model
        out_metrics: Where to save metrics JSON
        out_predictions: Where to save prediction JSONL
        n_trials: Number of Optuna hyperparameter tuning trials
        cv_splits: Number of GroupKFold splits for tuning
    """
    trainer = LGBMTrainer(n_trials=n_trials, cv_splits=cv_splits)

    # Load data
    X_train, y_train, feature_names, groups_train = trainer.load_data(train_parquet)
    X_val, y_val, _, _ = trainer.load_data(val_parquet)

    trainer.feature_names = feature_names

    # Normalize features
    X_train = trainer.scaler.fit_transform(X_train)
    X_val = trainer.scaler.transform(X_val)

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
    parser = argparse.ArgumentParser(description="Train LightGBM for RPA failure prediction")
    parser.add_argument("--train", type=str, required=True, help="Training Parquet with features")
    parser.add_argument("--val", type=str, required=True, help="Validation Parquet with features")
    parser.add_argument("--model", type=str, default="models/lgbm_model.txt", help="Output model path")
    parser.add_argument("--out-metrics", type=str, default="output/metrics.json", help="Output metrics JSON")
    parser.add_argument("--out-preds", type=str, default="output/predictions.jsonl", help="Output predictions JSONL")
    parser.add_argument("--n-trials", type=int, default=50, help="Optuna hyperparameter trials")
    parser.add_argument("--cv-splits", type=int, default=5, help="GroupKFold splits")

    args = parser.parse_args()
    train_lgbm_model(
        args.train, args.val, args.model, args.out_metrics, args.out_preds, args.n_trials, args.cv_splits
    )
