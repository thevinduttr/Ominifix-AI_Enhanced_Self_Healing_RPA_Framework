import re
import json
import joblib
import numpy as np
import pandas as pd

from pathlib import Path
from sklearn.model_selection import train_test_split, StratifiedKFold, GridSearchCV
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics import accuracy_score, classification_report
from sklearn.impute import SimpleImputer

from xgboost import XGBClassifier


DATA_PATH = Path("data/tuned_ptqa_training_data.csv")
OUT_PATH = Path("app/ml/artifacts/Tuned_ptqa_failure_model.joblib")
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)


def _tokenize(s: str) -> list[str]:
    return [t for t in re.split(r"[^a-zA-Z0-9]+", str(s).lower()) if t]


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def _common_prefix_len(a: str, b: str) -> int:
    a, b = str(a), str(b)
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def add_feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Ensure strings
    df["old_locator"] = df.get("old_locator", "").astype(str)
    df["new_locator"] = df.get("new_locator", "").astype(str)

    # Locator volatility
    df["locator_changed"] = (df["old_locator"] != df["new_locator"]).astype(int)
    df["old_len"] = df["old_locator"].str.len()
    df["new_len"] = df["new_locator"].str.len()
    df["len_delta"] = (df["new_len"] - df["old_len"]).abs()

    # Similarities
    char_sim = []
    tok_sim = []
    prefix_len = []
    has_xpath_old = []
    has_xpath_new = []
    has_css_old = []
    has_css_new = []

    for o, n in zip(df["old_locator"], df["new_locator"]):
        o_str, n_str = str(o), str(n)

        char_sim.append(_jaccard(set(o_str), set(n_str)))
        tok_sim.append(_jaccard(set(_tokenize(o_str)), set(_tokenize(n_str))))
        prefix_len.append(_common_prefix_len(o_str, n_str))

        lo = o_str.lower()
        ln = n_str.lower()
        has_xpath_old.append(int(lo.strip().startswith("//") or "xpath" in lo))
        has_xpath_new.append(int(ln.strip().startswith("//") or "xpath" in ln))
        has_css_old.append(int(("css" in lo) or ("#" in lo) or ("." in lo)))
        has_css_new.append(int(("css" in ln) or ("#" in ln) or ("." in ln)))

    df["char_jaccard"] = char_sim
    df["token_jaccard"] = tok_sim
    df["prefix_match_len"] = prefix_len
    df["has_xpath_old"] = has_xpath_old
    df["has_xpath_new"] = has_xpath_new
    df["has_css_old"] = has_css_old
    df["has_css_new"] = has_css_new

    # Timing features
    eps = 1e-6
    df["avg_exec_time_before"] = pd.to_numeric(df.get("avg_exec_time_before", 1.0), errors="coerce")
    df["avg_exec_time_after"] = pd.to_numeric(df.get("avg_exec_time_after", 1.0), errors="coerce")
    df["time_delta"] = df["avg_exec_time_after"] - df["avg_exec_time_before"]
    df["time_ratio"] = (df["avg_exec_time_after"] + eps) / (df["avg_exec_time_before"] + eps)

    # Confidence + history interactions
    df["model_confidence"] = pd.to_numeric(df.get("model_confidence", 0.5), errors="coerce")
    df["last_n_failures"] = pd.to_numeric(df.get("last_n_failures", 0), errors="coerce")
    df["conf_x_failures"] = df["model_confidence"] * df["last_n_failures"]

    # Strategy risk prior (can help)
    risk_prior = {"vision": 0.8, "hybrid": 0.6, "dom": 0.4, "css": 0.35, "visual-ocr": 0.65}
    df["strategy_risk_prior"] = df.get("strategy", df.get("strategy_used", "dom")).map(risk_prior).fillna(0.5)

    return df


def main():
    df = pd.read_csv(DATA_PATH)

    # Target: failed = 1
    y = df["failed"].astype(int)

    df = add_feature_engineering(df)

    # Choose features
    # Keep both possible names to be robust across your dataset variations
    df["strategy_cat"] = df.get("strategy", df.get("strategy_used", "dom")).astype(str)
    df["env_cat"] = df.get("environment", "prod").astype(str)
    df["bot_cat"] = df.get("bot_id", df.get("script_id", "BOT_UNKNOWN")).astype(str)

    numeric_features = [
        "model_confidence",
        "last_n_failures",
        "avg_exec_time_before",
        "avg_exec_time_after",
        "time_delta",
        "time_ratio",
        "conf_x_failures",
        "locator_changed",
        "old_len",
        "new_len",
        "len_delta",
        "char_jaccard",
        "token_jaccard",
        "prefix_match_len",
        "has_xpath_old",
        "has_xpath_new",
        "has_css_old",
        "has_css_new",
        "strategy_risk_prior",
    ]

    categorical_features = ["strategy_cat", "env_cat", "bot_cat"]

    X = df[numeric_features + categorical_features].copy()

    # Held-out split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    # Preprocess
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
        ]
    )

    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
        ]
    )

    # Model
    xgb = XGBClassifier(
        n_estimators=400,
        learning_rate=0.05,
        max_depth=5,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_lambda=1.0,
        random_state=42,
        eval_metric="logloss",
        n_jobs=-1,
    )

    pipe = Pipeline(steps=[("prep", preprocessor), ("model", xgb)])

    # Small grid search (fast, high ROI)
    param_grid = {
        "model__max_depth": [4, 5, 6],
        "model__subsample": [0.8, 0.9, 1.0],
        "model__colsample_bytree": [0.8, 0.9, 1.0],
    }

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    gs = GridSearchCV(
        pipe,
        param_grid=param_grid,
        scoring="accuracy",
        cv=cv,
        n_jobs=-1,
        verbose=1,
    )

    gs.fit(X_train, y_train)

    best_model = gs.best_estimator_
    print(f"Best params: {gs.best_params_}")
    print(f"CV mean accuracy (best): {gs.best_score_:.3f}")

    # Held-out test
    y_pred = best_model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"Held-out test accuracy: {acc:.3f}")
    print(classification_report(y_test, y_pred, digits=3))

    # Save artifact
    joblib.dump(best_model, OUT_PATH)
    print(f"Saved model to: {OUT_PATH.resolve()}")


if __name__ == "__main__":
    main()