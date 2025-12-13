import os
import random
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
import joblib

os.makedirs(os.path.join("data", "ml_dataset"), exist_ok=True)
os.makedirs(os.path.join("data", "models"), exist_ok=True)

def generate_synthetic_dataset(n=500):
    rows = []
    for _ in range(n):
        # Randomly choose if this row is correct candidate or not
        label = random.choice([0, 1])

        if label == 1:
            text_sim = random.uniform(0.7, 1.0)
            id_present = random.choice([0, 1])
            class_len = random.uniform(1, 4)
            is_button = 1
            is_link = 0
            role_match = 1
            cv_similarity = random.uniform(0.6, 1.0)
            cv_dist_norm = random.uniform(0.6, 1.0)
        else:
            text_sim = random.uniform(0.0, 0.5)
            id_present = random.choice([0, 1])
            class_len = random.uniform(0, 6)
            is_button = random.choice([0, 1])
            is_link = random.choice([0, 1])
            role_match = random.choice([0, 1])
            cv_similarity = random.uniform(0.0, 0.5)
            cv_dist_norm = random.uniform(0.0, 0.5)

        rows.append({
            "text_sim": text_sim,
            "id_present": id_present,
            "class_len": class_len,
            "is_button": is_button,
            "is_link": is_link,
            "role_match": role_match,
            "cv_similarity": cv_similarity,
            "cv_dist_norm": cv_dist_norm,
            "label": label
        })

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join("data", "ml_dataset", "locator_dataset.csv"), index=False)
    print("[+] Synthetic dataset created with", len(df), "rows.")
    return df

def train_model():
    csv_path = os.path.join("data", "ml_dataset", "locator_dataset.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
    else:
        df = generate_synthetic_dataset(800)

    X = df.drop("label", axis=1)
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = GradientBoostingClassifier()
    model.fit(X_train, y_train)
    acc = model.score(X_test, y_test)
    print("[+] Model trained. Accuracy:", acc)

    model_path = os.path.join("data", "models", "locator_gb.pkl")
    joblib.dump(model, model_path)
    print("[+] Model saved to", model_path)

if __name__ == "__main__":
    generate_synthetic_dataset(1000)
    train_model()
