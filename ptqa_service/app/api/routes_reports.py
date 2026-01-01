from fastapi import APIRouter

router = APIRouter()


@router.get("/report/{healing_id}")
def get_report(healing_id: str):
    return {"healing_id": healing_id, "status": "report endpoint placeholder"}
