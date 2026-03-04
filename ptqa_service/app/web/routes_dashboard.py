from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models_decisions import PTQADecision

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    runs = db.query(PTQADecision).order_by(PTQADecision.id.desc()).limit(50).all()
    return templates.TemplateResponse("dashboard.html", {"request": request, "runs": runs})


@router.get("/dashboard/report/{healing_id}", response_class=HTMLResponse)
def report_page(healing_id: str, request: Request, db: Session = Depends(get_db)):
    row = db.query(PTQADecision).filter(PTQADecision.healing_id == healing_id).first()
    return templates.TemplateResponse(
        "report.html", {"request": request, "row": row, "healing_id": healing_id}
    )


# NEW: delete a single run by healing_id
@router.delete("/dashboard/delete/{healing_id}")
def delete_run(healing_id: str, db: Session = Depends(get_db)):
    row = db.query(PTQADecision).filter(PTQADecision.healing_id == healing_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="healing_id not found")
    db.delete(row)
    db.commit()
    return {"deleted": True, "healing_id": healing_id}


# OPTIONAL: delete all runs
@router.delete("/dashboard/delete-all")
def delete_all(db: Session = Depends(get_db)):
    db.query(PTQADecision).delete()
    db.commit()
    return {"deleted_all": True}