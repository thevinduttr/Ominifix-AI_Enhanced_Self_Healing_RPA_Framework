"""
app.api

FastAPI application exposing the AI-Powered Element Locator Engine as a
microservice. This is the main entrypoint used by uvicorn.

Run locally with:
    uvicorn app.api:app --reload
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.locator_engine import ElementLocatorEngine
from app.core.models.contracts import FailureFromOrchestrator, LocatorEngineReport
from app.infra.logging_config import configure_logging
from app.infra.settings import settings

# Configure logging once at startup
configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI-Powered Element Locator Engine",
    version=settings.SERVICE_VERSION,
    description=(
        "Microservice responsible for analysing RPA element failures and "
        "producing robust replacement locators using multi-strategy analysis."
    ),
)

# --- CORS CONFIGURATION FOR REACT DASHBOARD ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single engine instance reused for all requests
locator_engine = ElementLocatorEngine()


@app.get("/health", tags=["system"])
def health_check() -> dict:
    """
    Lightweight liveness endpoint for orchestration and monitoring.
    """
    return {"status": "ok", "service": settings.SERVICE_NAME}


@app.post(
    "/element-locator/report",
    response_model=LocatorEngineReport,
    tags=["locator"],
)
def generate_locator_report(payload: FailureFromOrchestrator):
    """
    Main business endpoint.

    Receives a failure description from the Distributed Self-Healing
    Orchestrator and returns a LocatorEngineReport containing the best
    candidate element and its reliability score.
    """
    logger.info("Incoming /element-locator/report request")

    # Debug log: confirm vision fields arrive from dashboard / swagger
    logger.info(
        "Payload vision inputs: screenshot_path=%s template_path=%s page_html_provided=%s",
        payload.screenshot_path,
        payload.template_path,
        bool(payload.page_html),
    )
    
    report = locator_engine.locate_and_build_report(payload)
    return JSONResponse(content=report.model_dump(mode="json"))
