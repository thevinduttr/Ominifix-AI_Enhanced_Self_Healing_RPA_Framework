import joblib
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)
from sklearn.model_selection import train_test_split
import seaborn as sns
import matplotlib.pyplot as plt

# -----------------------------
# CONFIG
# -----------------------------
DATASET_PATH = "data/ml/healing_dataset.csv"
MODEL_PATH = "models/strategy_selector_v1.pkl"
LABEL_COLUMN = "strategy"

# -----------------------------
# LOAD DATA
# -----------------------------
df = pd.read_csv(DATASET_PATH)

print("Dataset size:", df.shape)
print("\nLabel distribution:")
print(df[LABEL_COLUMN].value_counts())

# -----------------------------
# FEATURE ENGINEERING
# (must match training logic)
# -----------------------------
# Combine important text fields
text_columns = [
    "error_type",
    "action",
    "old_locator",
    "new_element_html"
]

# Keep only columns that exist
text_columns = [c for c in text_columns if c in df.columns]

df["combined_text"] = df[text_columns].fillna("").agg(" ".join, axis=1)

X = df["combined_text"]
y = df[LABEL_COLUMN]

# -----------------------------
# TRAIN / TEST SPLIT
# -----------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    stratify=y,
    random_state=42
)

print("\nTrain size:", len(X_train))
print("Test size:", len(X_test))

# -----------------------------
# LOAD MODEL
# -----------------------------
model = joblib.load(MODEL_PATH)

print("\nModel loaded:", type(model))

# -----------------------------
# PREDICTION
# -----------------------------
y_pred = model.predict(X_test)

# -----------------------------
# METRICS
# -----------------------------
accuracy = accuracy_score(y_test, y_pred)

print("\n==============================")
print("MODEL EVALUATION RESULTS")
print("==============================")
print(f"Accuracy: {accuracy:.4f}\n")

print("Classification Report:")
print(classification_report(y_test, y_pred))

# -----------------------------
# CONFUSION MATRIX
# -----------------------------
cm = confusion_matrix(y_test, y_pred, labels=model.classes_)

plt.figure(figsize=(6, 4))
sns.heatmap(
    cm,
    annot=True,
    fmt="d",
    cmap="Blues",
    xticklabels=model.classes_,
    yticklabels=model.classes_
)
plt.xlabel("Predicted")
plt.ylabel("Actual")
plt.title("Strategy Selector Confusion Matrix")
plt.tight_layout()
plt.show()
