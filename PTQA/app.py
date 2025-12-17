import streamlit as st
import pandas as pd
import json
import joblib
from pathlib import Path
from src.features.extract_features import FeatureExtractor

# --- CONFIG ---
MODEL_PATH = "models/rf_10k_model.joblib"  # Update if your model path is different
FEATURE_NAMES_PATH = "models/feature_names.json"  # Update if needed
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Should match your training pipeline

st.set_page_config(page_title="RPA Failure Prediction Demo", layout="wide")
st.title("🤖 RPA Failure Prediction Demo")

st.markdown("""
Upload your RPA event logs (JSON or JSONL), and get instant predictions for each event.
- Supports file upload or pasting JSON content.
- Shows prediction (failure or not) and event details.
""")

# --- Load model and feature names ---
@st.cache_resource
def load_model():
    model = joblib.load(MODEL_PATH)
    return model

def load_feature_names():
    if Path(FEATURE_NAMES_PATH).exists():
        with open(FEATURE_NAMES_PATH) as f:
            return json.load(f)
    return None

model = load_model()
feature_names = load_feature_names()
extractor = FeatureExtractor(model_name=EMBEDDING_MODEL)

# --- Input UI ---
input_method = st.radio("Input method", ["Upload file", "Paste JSON/JSONL"], horizontal=True)

if input_method == "Upload file":
    uploaded_file = st.file_uploader("Upload event log file (JSON or JSONL)", type=["json", "jsonl"])
    raw_content = uploaded_file.read().decode() if uploaded_file else None
else:
    raw_content = st.text_area("Paste your event log(s) here", height=200)

# --- Parse events ---
def parse_events(raw):
    if not raw:
        return []
    try:
        # Try JSONL
        events = [json.loads(line) for line in raw.splitlines() if line.strip()]
        if len(events) == 1:
            # Try as single JSON array or object
            obj = json.loads(raw)
            if isinstance(obj, list):
                return obj
            elif isinstance(obj, dict):
                return [obj]
        return events
    except Exception:
        return []

events = parse_events(raw_content)

if events:
    st.success(f"Loaded {len(events)} event(s)")
    df = pd.DataFrame(events)
    # --- Feature extraction ---
    with st.spinner("Extracting features and predicting..."):
        features_df = extractor.extract_from_dataframe(df)
        # Align features to model
        if feature_names:
            missing = [f for f in feature_names if f not in features_df.columns]
            for f in missing:
                features_df[f] = 0
            features_df = features_df[feature_names]
        preds = model.predict(features_df)
    # --- Show results ---
    results = df.copy()
    results["Prediction"] = preds
    results["Prediction"] = results["Prediction"].map({0: "No Failure", 1: "Failure"})
    st.dataframe(results)
    st.download_button("Download results as CSV", results.to_csv(index=False), "predictions.csv")
else:
    st.info("Upload or paste your event logs to get started.")
