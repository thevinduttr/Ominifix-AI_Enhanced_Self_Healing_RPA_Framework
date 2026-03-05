# app/api/routes_healing.py

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.event_ingestor import ingest_healing_event
from app.core.data_collector import collect_execution_context
from app.core.feature_engineer import build_feature_vector
from app.adapters.healing_input_adapter import HealingInputAdapter

_adapter = HealingInputAdapter()
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
    # 0) Normalise input format (handles both PTQA native and Code Healing Engine formats)
    payload = _adapter.adapt(payload)

    # 1) Normalise event
    healing_event = ingest_healing_event(payload)
    healing_id = healing_event["healing_id"]

    # 2) Collect context
    context = collect_execution_context(healing_event)

    # 3) Features + prediction
    features = build_feature_vector(healing_event, context)
    prediction = run_prediction(features)

    # 4) Tests (generated once)
    tests = generate_validation_tests(healing_event)
    validation_steps = build_validation_steps_for_report(tests)

    # Extract script paths from payload
    script_output = healing_event.get("script_output", {}) or {}
    original_path = script_output.get("original_script_path")
    healed_path = script_output.get("healed_script_path")

    # Always attempt before/after if we have both paths
    before_results: dict
    after_results: dict

    if original_path and healed_path:
        # BEFORE
        try:
            before_results = run_regression_suite(
                tests, context, script_path_override=original_path
            )
        except FileNotFoundError as e:
            # return a consistent structure (so metrics won't crash)
            before_results = {
                "script_path": original_path,
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "avg_exec_time": 0.0,
                "details": [],
                "video_paths": [],
                "skipped": True,
                "reason": str(e),
            }

        # AFTER
        try:
            after_results = run_regression_suite(
                tests, context, script_path_override=healed_path
            )
        except FileNotFoundError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        # Backward compatible mode: only execute what tests already specify (healed)
        after_results = run_regression_suite(tests, context)
        before_results = {
            "script_path": original_path,
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "avg_exec_time": 0.0,
            "details": [],
            "video_paths": [],
            "skipped": True,
            "reason": "Baseline script path not provided; before-run skipped.",
        }

    # 5) Metrics (comparison)
    metrics = compute_quality_metrics(prediction, before_results, after_results)

    # 6) Quality gate
    decision = evaluate_quality(
        healing_id=healing_id,
        prediction=prediction,
        metrics=metrics,
        validation_steps=validation_steps,
    )

    # Attach before/after execution results
    decision["before_results"] = before_results
    decision["after_results"] = after_results

    # 7) Persist decision in SQLite (upsert by healing_id)
    metadata = healing_event.get("metadata", {}) or {}

    existing = db.query(PTQADecision).filter(PTQADecision.healing_id == healing_id).first()

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