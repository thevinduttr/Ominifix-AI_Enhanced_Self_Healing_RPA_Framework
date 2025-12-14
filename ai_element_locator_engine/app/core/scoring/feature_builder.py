"""
app.core.scoring.feature_builder

Transforms ElementCandidateInternal objects into numerical feature vectors
for the reliability model. The initial version keeps the feature set small
and uses only heuristic scores + a few core attributes.
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np

from app.core.models.internal import ElementCandidateInternal


FEATURE_NAMES = [
    "heuristic_score",
    "text_similarity",
    "id_similarity",
    "name_similarity",
]


def build_feature_matrix(candidates: List[ElementCandidateInternal]) -> Tuple[np.ndarray, list[str]]:
    """
    Build a 2D numpy array of shape (n_candidates, n_features) and return it
    together with the ordered list of feature names. Missing features default
    to zero.
    """
    matrix: list[list[float]] = []

    for c in candidates:
        row = [
            float(c.heuristic_score),
            float(c.features.get("text_similarity", 0.0)),
            float(c.features.get("id_similarity", 0.0)),
            float(c.features.get("name_similarity", 0.0)),
        ]
        matrix.append(row)

    if not matrix:
        return np.zeros((0, len(FEATURE_NAMES))), FEATURE_NAMES

    return np.array(matrix, dtype=float), FEATURE_NAMES
