"""
app.api

FastAPI application exposing the AI-Powered Element Locator Engine as a
microservice. This is the main entrypoint used by uvicorn.

Run locally with:
    uvicorn app.api:app --reload
"""

from __future__ import annotations

import logging
import time

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import requests

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


def _build_healing_payload(payload: FailureFromOrchestrator, report: LocatorEngineReport) -> dict:
    metadata = report.metadata.model_dump() if report.metadata else {}
    failure_context = report.failure_context.model_dump() if report.failure_context else {}
    dom_context = report.dom_context.model_dump() if report.dom_context else {}
    expectation = report.element_expectation.model_dump() if report.element_expectation else {}
    candidate = report.element_candidate.model_dump() if report.element_candidate else None

    script_path = (
        failure_context.get("script_path")
        or payload.metadata.get("script_path")
        or "data/scripts/broken/auto_generated.py"
    )
    failing_line_raw = failure_context.get("failing_line") or payload.metadata.get("failing_line") or 1
    try:
        failing_line = int(failing_line_raw)
    except (TypeError, ValueError):
        failing_line = 1

    action = failure_context.get("action") or payload.failed_action or "click"
    error_type = failure_context.get("error_type") or payload.failure_type or "ELEMENT_NOT_FOUND"
    old_locator = failure_context.get("old_locator") or payload.old_locator or ""
    error_message = (
        failure_context.get("error_message")
        or payload.error_message
        or "Auto forwarded from ai_element_locator_engine"
    )
    new_element_html = dom_context.get("new_element_html") or payload.page_html or ""

    element_candidate = None
    if candidate:
        raw_score = candidate.get("score")
        score = None
        if raw_score is not None:
            try:
                val = float(raw_score)
                score = round(val * 100.0, 2) if val <= 1.0 else round(val, 2)
            except (TypeError, ValueError):
                score = None

        element_candidate = {
            "css": candidate.get("css"),
            "xpath": candidate.get("xpath"),
            "full_xpath": candidate.get("full_xpath"),
            "score": score,
            "strategy": candidate.get("strategy"),
        }

    return {
        "metadata": {
            "schema_version": "1.0",
            "report_id": metadata.get("report_id") or f"ELR-AUTO-{int(time.time() * 1000)}",
            "run_id": metadata.get("run_id") or payload.metadata.get("run_id") or "",
            "bot_id": payload.metadata.get("bot_id") or "UNKNOWN_BOT",
            "timestamp": str(metadata.get("timestamp") or ""),
            "source_component": settings.SERVICE_NAME,
            "target_component": "code_healing_engine",
            "environment": payload.metadata.get("environment") or "docker",
        },
        "failure_context": {
            "script_path": script_path,
            "failing_line": failing_line,
            "action": action,
            "old_locator": old_locator,
            "error_type": error_type,
            "error_message": error_message,
        },
        "dom_context": {
            "new_element_html": new_element_html,
            "page_url": dom_context.get("page_url") or payload.page_url or "",
            "page_name": dom_context.get("page_name") or payload.metadata.get("page_name") or "",
        },
        "element_expectation": {
            "expected_role": expectation.get("expected_role") or payload.element_role or "",
            "expected_text": expectation.get("expected_text") or payload.expected_text or "",
        },
        "element_candidate": element_candidate,
    }


def _forward_to_healing_engine(healing_payload: dict) -> tuple[dict | None, str | None]:
    try:
        resp = requests.post(
            settings.HEALING_ENGINE_URL,
            json=healing_payload,
            timeout=(5, settings.HEALING_ENGINE_TIMEOUT_SECONDS),
        )
        if not resp.ok:
            return None, f"HTTP {resp.status_code}: {resp.text[:300]}"
        return resp.json(), None
    except Exception as exc:
        return None, str(exc)


@app.get("/", tags=["system"])
def root() -> dict:
    return {
        "status": "ok",
        "service": settings.SERVICE_NAME,
        "health": "/health",
        "docs": "/docs",
    }


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
    response_body = report.model_dump(mode="json")

    healing_payload = _build_healing_payload(payload, report)
    healing_result, healing_error = _forward_to_healing_engine(healing_payload)
    response_body["healing_request"] = healing_payload
    response_body["healing_result"] = healing_result
    response_body["healing_error"] = healing_error

    if healing_error:
        logger.warning("Healing engine forwarding failed: %s", healing_error)
    else:
        hs = (healing_result or {}).get("healing_summary", {})
        logger.info(
            "Forwarded to healing engine: status=%s strategy=%s",
            hs.get("status"),
            hs.get("strategy_used"),
        )

    return JSONResponse(content=response_body)
