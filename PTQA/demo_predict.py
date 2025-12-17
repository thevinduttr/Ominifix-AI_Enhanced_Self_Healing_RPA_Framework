import json
import pandas as pd
from src.features.extract_features import FeatureExtractor
import joblib
import glob
import os


with open("models/feature_names.json", "r") as f:
    expected_features = json.load(f)

model = joblib.load("models/rf_10k_model.joblib")


event_files = glob.glob("event*.json")
if not event_files:
    print("No event JSON files found. Please add files named event1.json, event2.json, ...")
    exit(1)

for event_file in event_files:
    with open(event_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    event = {
        "timestamp": data["metadata"]["timestamp"],
        "session": data["metadata"].get("healing_id", "default_session"),
        "type": data["healing_summary"].get("strategy_used", "unknown"),
        "selector": data["healing_summary"].get("old_locator", ""),
        "message": f"{data['healing_summary']['status']} | {data['healing_summary']['strategy_used']} | {data['healing_summary']['old_locator']} -> {data['healing_summary']['new_locator']}",
        "status": data["healing_summary"]["status"]
    }
    df = pd.DataFrame([event])
    extractor = FeatureExtractor()
    features_df = extractor.extract_from_dataframe(df)
    # Add missing columns with zeros
    for col in expected_features:
        if col not in features_df.columns:
            features_df[col] = 0
    # Ensure correct column order
    X = features_df[expected_features]
    preds = model.predict(X)
    label = preds[0]
    if label == 0:
        result = "No failure detected (class 0)"
    else:
        result = "Failure detected (class 1)"
    print(f"\nFile: {event_file}")
    print(f"Prediction: {label} — {result}")
    print(f"Event details:")
    print(f"  Timestamp: {event['timestamp']}")
    print(f"  Session: {event['session']}")
    print(f"  Strategy: {event['type']}")
    print(f"  Selector: {event['selector']}")
    print(f"  Message: {event['message']}")
    print(f"  Status: {event['status']}")
    print("-"*40)