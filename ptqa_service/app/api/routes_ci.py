from fastapi import APIRouter

router = APIRouter()


@router.post("/ci/check")
def ci_quality_gate(payload: dict):
    return {"message": "CI quality gate placeholder", "status": "OK"}
