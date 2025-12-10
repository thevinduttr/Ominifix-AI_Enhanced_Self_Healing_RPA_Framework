import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models_decisions import PTQADecision

router = APIRouter()


@router.get("/report/{healing_id}")
def get_report(healing_id: str, db: Session = Depends(get_db)):
    """
    Return a detailed PTQA report for a given healing_id,
    based on the persisted decision in SQLite.
    """
    db_decision = (
        db.query(PTQADecision)
        .filter(PTQADecision.healing_id == healing_id)
        .first()
    )

    if db_decision is None:
        raise HTTPException(status_code=404, detail="PTQA decision not found")

    # Parse stored JSON strings back to Python lists/dicts
    try:
        validation_steps = (
            json.loads(db_decision.validation_steps)
            if db_decision.validation_steps
            else []
        )
    except json.JSONDecodeError:
        validation_steps = []

    try:
        reasons = (
            json.loads(db_decision.reasons)
            if db_decision.reasons
            else []
        )
    except json.JSONDecodeError:
        reasons = []

    try:
        original_event = (
            json.loads(db_decision.raw_payload)
            if db_decision.raw_payload
            else {}
        )
    except json.JSONDecodeError:
        original_event = {}

    report = {
        "healing_id": db_decision.healing_id,
        "script_id": db_decision.script_id,
        "environment": db_decision.environment,
        "model_name": db_decision.model_name,
        "will_work_probability": db_decision.will_work_probability,
        "risk_level": db_decision.risk_level,
        "recommendation": db_decision.recommendation,
        "confidence": db_decision.confidence,
        "quality_metrics": {
            "healing_accuracy": db_decision.healing_accuracy,
            "recovery_latency": db_decision.recovery_latency,
            "reliability_score": db_decision.reliability_score,
        },
        "validation_steps": validation_steps,
        "reasons": reasons,
        "original_event": original_event,
        "created_at": db_decision.created_at.isoformat() if db_decision.created_at else None,
    }

    return report
