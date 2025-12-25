import os
import json
import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import GradientBoostingClassifier

DATASET_PATH = os.path.join("data", "dataset", "dom_training_big.csv")
MODEL_DIR = os.path.join("data", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "dom_locator_model.pkl")
FEATURES_PATH = os.path.join(MODEL_DIR, "dom_feature_columns.json")
METRICS_PATH = os.path.join(MODEL_DIR, "dom_metrics.json")

os.makedirs(MODEL_DIR, exist_ok=True)

def make_ohe():
    # sklearn compatibility
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)

print("[+] Loading dataset...")
df = pd.read_csv(DATASET_PATH)
print(f"[+] Rows: {len(df)}")

LABEL_COL = "label"
y = df[LABEL_COL]

# Remove columns not used in learning
DROP_COLS = ["full_xpath", "outer_html"]
X = df.drop(columns=[LABEL_COL] + [c for c in DROP_COLS if c in df.columns])

NUMERIC_FEATURES = [
    "expected_text_len",
    "text_len",
    "has_id",
    "has_name",
    "has_class",
    "has_aria",
    "has_placeholder",
    "expected_in_text",
    "expected_in_attrs"
]

CATEGORICAL_FEATURES = [
    "action",
    "expected_role",
    "tag",
    "type"
]

missing_num = [c for c in NUMERIC_FEATURES if c not in X.columns]
missing_cat = [c for c in CATEGORICAL_FEATURES if c not in X.columns]
if missing_num or missing_cat:
    raise ValueError(f"Missing columns: numeric={missing_num}, categorical={missing_cat}")

preprocessor = ColumnTransformer(
    transformers=[
        ("num", "passthrough", NUMERIC_FEATURES),
        ("cat", make_ohe(), CATEGORICAL_FEATURES),
    ],
    remainder="drop"
)

model = GradientBoostingClassifier(
    n_estimators=350,
    learning_rate=0.05,
    max_depth=5,
    random_state=42
)

pipeline = Pipeline(
    steps=[
        ("preprocess", preprocessor),
        ("model", model)
    ]
)

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    stratify=y,
    random_state=42
)

print("[+] Training model...")
pipeline.fit(X_train, y_train)

print("[+] Evaluating model...")
y_pred = pipeline.predict(X_test)
y_prob = pipeline.predict_proba(X_test)[:, 1]

metrics = {
    "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
    "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
    "recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
    "f1": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
    "roc_auc": round(float(roc_auc_score(y_test, y_prob)), 4),
    "train_rows": int(len(X_train)),
    "test_rows": int(len(X_test)),
    "positive_rate": round(float(y.mean()), 6)
}

print("\n=== Metrics ===")
for k, v in metrics.items():
    print(f"{k}: {v}")

print("[+] Saving model...")
joblib.dump(pipeline, MODEL_PATH)

feature_info = {
    "numeric_features": NUMERIC_FEATURES,
    "categorical_features": CATEGORICAL_FEATURES,
    "dropped_features": DROP_COLS
}

with open(FEATURES_PATH, "w", encoding="utf-8") as f:
    json.dump(feature_info, f, indent=2)

with open(METRICS_PATH, "w", encoding="utf-8") as f:
    json.dump(metrics, f, indent=2)

print("\n[OK] Model saved:", MODEL_PATH)
print("[OK] Metrics saved:", METRICS_PATH)
