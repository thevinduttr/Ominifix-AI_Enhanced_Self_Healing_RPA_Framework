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
    report = locator_engine.locate_and_build_report(payload)
    return JSONResponse(content=report.model_dump(mode="json"))
