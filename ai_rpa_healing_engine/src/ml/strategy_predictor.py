from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import joblib


@dataclass
class StrategyPrediction:
    label: str
    confidence: float


class StrategyPredictor:
    """
    Loads a sklearn Pipeline (TF-IDF + classifier) saved via joblib from Kaggle,
    and predicts healing strategy from the current failure context.
    """

    def __init__(self, model_path: str = "models/strategy_selector_v1.pkl"):
        mp = Path(model_path)
        if not mp.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        self.model = joblib.load(mp)

    @staticmethod
    def build_feature_text(error_type: str, old_locator: str, element_html: str) -> str:
        return f"{error_type} {old_locator} {element_html}".strip()

    def predict(self, error_type: str, old_locator: str, element_html: str) -> StrategyPrediction:
        text = self.build_feature_text(error_type, old_locator, element_html)

        # Predict label
        label = self.model.predict([text])[0]

        # Predict confidence (max class probability) if supported
        conf = 0.0
        if hasattr(self.model, "predict_proba"):
            probs = self.model.predict_proba([text])[0]
            conf = float(max(probs))
        else:
            # fallback: no proba support
            conf = 0.0

        return StrategyPrediction(label=str(label), confidence=conf)
