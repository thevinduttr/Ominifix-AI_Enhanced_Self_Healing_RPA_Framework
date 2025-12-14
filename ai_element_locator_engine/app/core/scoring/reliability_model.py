"""
app.core.scoring.reliability_model

Wrapper around the ML model used to estimate final reliability scores for
candidate elements. If a trained model is not yet available, we fall back
to using the heuristic_score directly.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.exceptions import NotFittedError
from joblib import load

from app.core.models.internal import ElementCandidateInternal
from app.core.scoring.feature_builder import build_feature_matrix

logger = logging.getLogger(__name__)


class ReliabilityModel:
    def __init__(self, model_path: str | Path = "data/models/reliability_model.pkl"):
        self.model_path = Path(model_path)
        self.model: RandomForestClassifier | None = None

        if self.model_path.exists():
            try:
                self.model = load(self.model_path)
                logger.info("Loaded reliability model from %s", self.model_path)
            except Exception as exc:
                logger.error("Failed to load reliability model: %s", exc)
                self.model = None
        else:
            logger.warning(
                "Reliability model not found at %s; heuristic scoring will be used.",
                self.model_path,
            )

    def score_candidates(self, candidates: List[ElementCandidateInternal]) -> None:
        """
        Mutates each candidate in-place by setting its `final_score`.

        If no ML model is available or it is not fitted, the heuristic_score
        is simply copied into final_score.
        """
        if not candidates:
            return

        X, _ = build_feature_matrix(candidates)

        if self.model is None:
            for c in candidates:
                c.final_score = float(c.heuristic_score)
            return

        try:
            proba: np.ndarray = self.model.predict_proba(X)[:, 1]
        except NotFittedError:
            logger.error("Reliability model exists but is not fitted; using heuristics.")
            for c in candidates:
                c.final_score = float(c.heuristic_score)
            return

        for c, p in zip(candidates, proba):
            c.final_score = float(p)
