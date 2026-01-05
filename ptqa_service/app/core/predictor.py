from typing import Dict

from app.ml.features import dict_to_vector
from app.ml.model_loader import load_model


def run_prediction(features: Dict[str, float]) -> Dict[str, object]:
    """
    Use the trained ensemble model to estimate failure probability.
    """
    model = load_model()
    X = dict_to_vector(features)

    proba = model.predict_proba(X)[0]
    # assume class "1" = failure
    class_idx = list(model.classes_).index(1)
    p_fail = float(proba[class_idx])

    if p_fail < 0.3:
        risk_level = "LOW"
    elif p_fail < 0.6:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"

    model_label = getattr(
        model,
        "model_label",
        type(model).__name__,
    )

    return {
        "model_name": model_label,
        "p_fail": p_fail,
        "risk_level": risk_level,
        "will_work_probability": 1.0 - p_fail,
    }
