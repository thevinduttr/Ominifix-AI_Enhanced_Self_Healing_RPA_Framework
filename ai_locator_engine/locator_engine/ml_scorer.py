# import os
# import joblib

# MODEL_PATH = os.path.join("data", "models", "locator_gb.pkl")

# _model = None

# def load_model():
#     global _model
#     if _model is None:
#         if not os.path.exists(MODEL_PATH):
#             raise FileNotFoundError("Model not found. Train it with train_ml_model.py.")
#         _model = joblib.load(MODEL_PATH)
#     return _model


# def score_candidate(feature_vector):
#     model = load_model()
#     import numpy as np
#     x = np.array(feature_vector).reshape(1, -1)
#     proba = model.predict_proba(x)[0][1]
#     return float(proba)

import os
import joblib
import numpy as np

MODEL_PATH = os.path.join("data", "models", "dom_ranker.pkl")
_model = None

def load_model():
    global _model
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError("DOM model not found. Train it with train/train_dom_model.py.")
        _model = joblib.load(MODEL_PATH)
    return _model

def score_dom_features(feature_dict: dict) -> float:
    model = load_model()
    X = np.array(list(feature_dict.values()), dtype=float).reshape(1, -1)
    if hasattr(model, "predict_proba"):
        return float(model.predict_proba(X)[0][1])
    return float(model.predict(X)[0])
