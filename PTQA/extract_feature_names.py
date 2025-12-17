import pandas as pd
import json

# Load features from synthetic_10k_features.parquet
features_path = "dataset/synthetic_10k_features.parquet"
df = pd.read_parquet(features_path)
drop_cols = ["label", "timestamp", "session", "component", "type", "selector", "message", "status", "meta"]
if "features" in df.columns:
    drop_cols.append("features")
feature_names = [c for c in df.columns if c not in drop_cols]

with open("models/feature_names.json", "w") as f:
    json.dump(feature_names, f)

print("✓ Feature names saved to models/feature_names.json")
