from pathlib import Path
from typing import Any

import joblib
from sklearn.base import BaseEstimator

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "ptqa_failure_model.joblib"

_model_cache: BaseEstimator | None = None


def load_model() -> BaseEstimator:
    global _model_cache
    if _model_cache is None:
        if not MODEL_PATH.exists():
            raise RuntimeError(
                f"Model file not found at {MODEL_PATH}. "
                "Train the model first using train_pipeline.py"
            )
        _model_cache = joblib.load(MODEL_PATH)
    return _model_cache
