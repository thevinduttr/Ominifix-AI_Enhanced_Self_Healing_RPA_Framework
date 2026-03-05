"""
Tests for StrategyPredictor — ML model loading and prediction.

Tests:
  - Smoke test: model loads without error
  - Prediction returns StrategyPrediction with valid label and 0.0–1.0 confidence
  - Predicted label is one of the known strategy classes
  - Feature text builder works correctly
  - Model handles edge-case inputs (empty strings)
"""

import pytest
from pathlib import Path

from src.ml.strategy_predictor import StrategyPredictor, StrategyPrediction


MODEL_PATH = "models/strategy_selector_v1.pkl"
VALID_STRATEGIES = {
    "LOCATOR_REGEN_LIBCST",
    "FALLBACK_LOCATOR",
    "FALLBACK_XPATH",
    "CLICK_ONLY",
    "NO_FIX",
}


@pytest.fixture
def predictor():
    if not Path(MODEL_PATH).exists():
        pytest.skip("Trained model not found — run train_strategy_model first")
    return StrategyPredictor(MODEL_PATH)


class TestModelLoading:
    def test_model_loads_successfully(self, predictor):
        """Smoke test — model loads and has predict methods."""
        assert predictor.model is not None
        assert hasattr(predictor.model, "predict")

    def test_invalid_path_raises(self):
        with pytest.raises(FileNotFoundError):
            StrategyPredictor("models/nonexistent.pkl")


class TestPrediction:
    def test_returns_strategy_prediction(self, predictor):
        result = predictor.predict(
            error_type="ELEMENT_NOT_FOUND",
            old_locator='input[name="email_old"]',
            element_html='<input id="email" type="email" />',
        )
        assert isinstance(result, StrategyPrediction)

    def test_label_is_valid_strategy(self, predictor):
        result = predictor.predict(
            error_type="ELEMENT_NOT_FOUND",
            old_locator='input[name="email_old"]',
            element_html='<input id="email" type="email" />',
        )
        assert result.label in VALID_STRATEGIES

    def test_confidence_in_valid_range(self, predictor):
        result = predictor.predict(
            error_type="TIMEOUT_WAITING_FOR_SELECTOR",
            old_locator='#submit_old',
            element_html='<button id="submitBtn">Submit</button>',
        )
        assert 0.0 <= result.confidence <= 1.0

    def test_click_action_predicts_click_only(self, predictor):
        """Click-related failure should predict CLICK_ONLY strategy."""
        result = predictor.predict(
            error_type="ELEMENT_NOT_FOUND",
            old_locator='button.save-wrong',
            element_html='<button id="saveBtn" aria-label="Save changes">Save</button>',
        )
        assert result.label == "CLICK_ONLY"

    def test_id_element_predicts_locator_regen(self, predictor):
        """Element with id should predict LOCATOR_REGEN_LIBCST."""
        result = predictor.predict(
            error_type="ELEMENT_NOT_FOUND",
            old_locator='input[name="old_field"]',
            element_html='<input id="email" type="email" placeholder="Email" />',
        )
        assert result.label == "LOCATOR_REGEN_LIBCST"

    def test_no_id_predicts_fallback_locator(self, predictor):
        """Element without id but with name/aria should predict FALLBACK_LOCATOR."""
        result = predictor.predict(
            error_type="ELEMENT_NOT_FOUND",
            old_locator='textarea[name="qqq"]',
            element_html='<textarea class="gLFyf" name="q" aria-label="Search"></textarea>',
        )
        assert result.label == "FALLBACK_LOCATOR"


class TestFeatureBuilder:
    def test_build_feature_text(self):
        text = StrategyPredictor.build_feature_text(
            error_type="ELEMENT_NOT_FOUND",
            old_locator="#old",
            element_html='<input id="new" />',
        )
        assert "ELEMENT_NOT_FOUND" in text
        assert "#old" in text
        assert '<input id="new" />' in text

    def test_build_feature_text_strips(self):
        text = StrategyPredictor.build_feature_text("", "", "")
        assert text == ""


class TestEdgeCases:
    def test_empty_inputs_dont_crash(self, predictor):
        """Model should not crash on empty inputs."""
        result = predictor.predict(
            error_type="",
            old_locator="",
            element_html="",
        )
        assert isinstance(result, StrategyPrediction)
        assert 0.0 <= result.confidence <= 1.0
