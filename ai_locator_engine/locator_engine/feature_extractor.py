# Build ML input from candidate + failure context
import numpy as np
from typing import Dict


def jaccard(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    sa = set(a.lower().split())
    sb = set(b.lower().split())
    inter = len(sa & sb)
    union = len(sa | sb) or 1
    return inter / union


def text_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    a = a.strip().lower()
    b = b.strip().lower()
    return 1.0 if a == b else jaccard(a, b)


def candidate_to_features(candidate: Dict,
                          failure_context: Dict,
                          cv_info: Dict = None):
    """
    Builds a feature vector for ML from DOM + CV + context.
    """
    expected_text = failure_context.get("expected_text") or ""
    role = failure_context.get("element_role") or ""

    # DOM-based features
    f_text_sim = text_similarity(candidate.get("text"), expected_text)
    f_id_present = 1.0 if candidate.get("id") else 0.0
    f_class_len = float(len((candidate.get("class") or "").split()))
    f_is_button = 1.0 if candidate.get("tag") == "button" else 0.0
    f_is_link = 1.0 if candidate.get("tag") == "a" else 0.0
    f_rough_role_match = 1.0 if candidate.get("rough_role") == role else 0.0

    # CV features (if any)
    cv_sim = cv_info.get("similarity", 0.0) if cv_info else 0.0
    cv_dist = cv_info.get("distance", 1000.0) if cv_info else 1000.0
    f_cv_sim = float(cv_sim)
    f_cv_dist_norm = float(np.exp(-cv_dist / 500.0)) if cv_dist is not None else 0.0

    feature_vector = [
        f_text_sim,
        f_id_present,
        f_class_len,
        f_is_button,
        f_is_link,
        f_rough_role_match,
        f_cv_sim,
        f_cv_dist_norm,
    ]

    feature_names = [
        "text_sim",
        "id_present",
        "class_len",
        "is_button",
        "is_link",
        "role_match",
        "cv_similarity",
        "cv_dist_norm",
    ]

    return feature_vector, feature_names
