import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models_decisions import PTQADecision

router = APIRouter()


@router.post("/ci/check")
def ci_check(payload: dict, db: Session = Depends(get_db)):
    """
    CI/CD quality gate endpoint.

    Expected payload:
    {
      "healing_id": "HEAL-2025-12-18-001"
    }

    Returns a compact decision suitable for use
    in GitHub Actions / Jenkins / Azure DevOps.
    """
    healing_id = payload.get("healing_id")
    if not healing_id:
        raise HTTPException(status_code=400, detail="healing_id is required")

    db_decision = (
        db.query(PTQADecision)
        .filter(PTQADecision.healing_id == healing_id)
        .first()
    )

    if db_decision is None:
        raise HTTPException(status_code=404, detail="PTQA decision not found")

    # Map internal recommendation to CI decision
    rec = db_decision.recommendation or "WARN"
    if rec == "APPROVE_HEALING":
        ci_decision = "ALLOW"
    elif rec == "BLOCK_HEALING":
        ci_decision = "BLOCK"
    else:
        ci_decision = "WARN"

    try:
        reasons = (
            json.loads(db_decision.reasons)
            if db_decision.reasons
            else []
        )
    except json.JSONDecodeError:
        reasons = []

    try:
        validation_steps = (
            json.loads(db_decision.validation_steps)
            if db_decision.validation_steps
            else []
        )
    except json.JSONDecodeError:
        validation_steps = []

    response = {
        "healing_id": db_decision.healing_id,
        "ci_decision": ci_decision,  # ALLOW / WARN / BLOCK
        "original_recommendation": rec,
        "risk_level": db_decision.risk_level,
        "will_work_probability": db_decision.will_work_probability,
        "confidence": db_decision.confidence,
        "quality_metrics": {
            "healing_accuracy": db_decision.healing_accuracy,
            "recovery_latency": db_decision.recovery_latency,
            "reliability_score": db_decision.reliability_score,
        },
        "validation_steps": validation_steps,
        "reasons": reasons,
    }

    return response
