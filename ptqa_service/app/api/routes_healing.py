from fastapi import APIRouter

from app.core.event_ingestor import ingest_healing_event
from app.core.data_collector import collect_execution_context
from app.core.feature_engineer import build_feature_vector
from app.core.predictor import run_prediction
from app.core.test_generator import (
    generate_validation_tests,
    build_validation_steps_for_report,
)
from app.core.test_runner import run_regression_suite
from app.core.metrics_engine import compute_quality_metrics
from app.core.quality_gate import evaluate_quality

router = APIRouter()


@router.post("/evaluate-healing")
def evaluate_healing(payload: dict):
    # 1. Ingest / normalize
    healing_event = ingest_healing_event(payload)
    healing_id = healing_event["healing_id"]

    # 2. Context
    context = collect_execution_context(healing_event)

    # 3. Feature engineering + ML prediction
    features = build_feature_vector(healing_event, context)
    prediction = run_prediction(features)

    # 4. Test generation + execution
    tests = generate_validation_tests(healing_event)
    test_results = run_regression_suite(tests, context)
    validation_steps = build_validation_steps_for_report(tests)

    # 5. Metrics
    metrics = compute_quality_metrics(prediction, test_results)

    # 6. Final decision
    decision = evaluate_quality(
        healing_id=healing_id,
        prediction=prediction,
        metrics=metrics,
        validation_steps=validation_steps,
    )

    return decision
