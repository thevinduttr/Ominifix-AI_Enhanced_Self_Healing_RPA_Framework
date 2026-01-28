"""
app.core.scoring.reliability_model

Wrapper around the ML model used to estimate final reliability scores for
candidate elements. 

Important fix for VisionStrategy:
- The ML model is trained mainly on DOM-derived features, so vision-only
  candidates can get artificially low probabilities.
- We therefore apply a safeguard: for vision candidates, final_score is
  at least their heuristic_score (or a weighted mix, configurable).

If a trained model is not available, we fall back to heuristic_score.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.exceptions import NotFittedError
from joblib import load

from app.core.models.internal import ElementCandidateInternal
from app.core.scoring.feature_builder import build_feature_matrix

logger = logging.getLogger(__name__)

VISION_STRATEGY_NAME = "vision_template_match"

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

        Vision fix:
        - For VisionStrategy candidates, final_score is clamped to be at least
          heuristic_score to avoid ML under-confidence on vision-only features.
        """
        if not candidates:
            return
        
        # Always have a safe baseline
        for c in candidates:
            c.final_score = float(c.heuristic_score)

        # If model not available, stop here (heuristics already applied)
        if self.model is None:
            return

        try:
            X, _ = build_feature_matrix(candidates)
        except Exception as exc:
            logger.exception("Failed to build feature matrix; using heuristics only: %s", exc)
            return

        try:
            proba: np.ndarray = self.model.predict_proba(X)[:, 1]
        except NotFittedError:
            logger.error("Reliability model exists but is not fitted; using heuristics only.")
            return
        except Exception as exc:
            logger.exception("Reliability model scoring failed; using heuristics only: %s", exc)
            return

        # Apply ML scores, then enforce vision safeguard
        for c, p in zip(candidates, proba):
            ml_score = float(p)

            # Default behavior: ML score wins
            final = ml_score

            # Vision safeguard: don't allow ML to push below heuristic
            if c.strategy == VISION_STRATEGY_NAME:
                final = max(ml_score, float(c.heuristic_score))

            c.final_score = final
