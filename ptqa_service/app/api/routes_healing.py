import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

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
from app.db.session import get_db
from app.db.models_decisions import PTQADecision

router = APIRouter()


@router.post("/evaluate-healing")
def evaluate_healing(payload: dict, db: Session = Depends(get_db)):
    # 1) Normalise event
    healing_event = ingest_healing_event(payload)
    healing_id = healing_event["healing_id"]

    # 2) Collect context
    context = collect_execution_context(healing_event)

    # 3) Features + prediction
    features = build_feature_vector(healing_event, context)
    prediction = run_prediction(features)

    # 4) Tests
    tests = generate_validation_tests(healing_event)
    test_results = run_regression_suite(tests, context)
    validation_steps = build_validation_steps_for_report(tests)

    # 5) Metrics
    metrics = compute_quality_metrics(prediction, test_results)

    # 6) Quality gate
    decision = evaluate_quality(
        healing_id=healing_id,
        prediction=prediction,
        metrics=metrics,
        validation_steps=validation_steps,
    )

    # 7) Persist decision in SQLite (upsert by healing_id)
    metadata = healing_event.get("metadata", {}) or {}

    existing = db.query(PTQADecision).filter(
        PTQADecision.healing_id == healing_id
    ).first()

    if existing is None:
        db_decision = PTQADecision(
            healing_id=healing_id,
            script_id=metadata.get("script_id") or metadata.get("bot_id"),
            environment=metadata.get("environment"),
            will_work_probability=decision["will_work_probability"],
            risk_level=decision["risk_level"],
            recommendation=decision["recommendation"],
            confidence=decision["confidence"],
            model_name=decision.get("model_name"),
            healing_accuracy=metrics.get("healing_accuracy"),
            recovery_latency=metrics.get("recovery_latency"),
            reliability_score=metrics.get("reliability_score"),
            validation_steps=json.dumps(decision.get("validation_steps", [])),
            reasons=json.dumps(decision.get("reasons", [])),
            raw_payload=json.dumps(healing_event.get("raw_payload", {})),
        )
        db.add(db_decision)
    else:
        # update existing record
        existing.script_id = metadata.get("script_id") or metadata.get("bot_id")
        existing.environment = metadata.get("environment")
        existing.will_work_probability = decision["will_work_probability"]
        existing.risk_level = decision["risk_level"]
        existing.recommendation = decision["recommendation"]
        existing.confidence = decision["confidence"]
        existing.model_name = decision.get("model_name")
        existing.healing_accuracy = metrics.get("healing_accuracy")
        existing.recovery_latency = metrics.get("recovery_latency")
        existing.reliability_score = metrics.get("reliability_score")
        existing.validation_steps = json.dumps(decision.get("validation_steps", []))
        existing.reasons = json.dumps(decision.get("reasons", []))
        existing.raw_payload = json.dumps(healing_event.get("raw_payload", {}))

    db.commit()

    return decision
