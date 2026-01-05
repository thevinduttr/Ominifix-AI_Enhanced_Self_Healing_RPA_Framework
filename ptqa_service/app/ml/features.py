from typing import Dict, List, Tuple
import numpy as np

# Define the canonical feature order for the model
FEATURE_NAMES: List[str] = [
    "model_confidence",
    "is_success_status",
    "locator_changed",
    "is_visual_strategy",
    "last_n_failures",
    "avg_exec_time_before",
    "avg_exec_time_after",
]


def dict_to_vector(features: Dict[str, float]) -> np.ndarray:
    """Convert a feature dict into a 2D numpy array [1, n_features]."""
    values = [float(features.get(name, 0.0)) for name in FEATURE_NAMES]
    return np.array(values, dtype=float).reshape(1, -1)


def vector_to_dict(values: np.ndarray) -> Dict[str, float]:
    """(Optional) Reverse mapping, useful for debugging."""
    return {name: float(v) for name, v in zip(FEATURE_NAMES, values.flatten())}


def get_feature_names() -> List[str]:
    return FEATURE_NAMES.copy()
