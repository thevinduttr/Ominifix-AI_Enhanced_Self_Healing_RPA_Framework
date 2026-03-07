"""
Code Healing Engine — REST API
===============================

FastAPI application that exposes the healing engine as HTTP endpoints
for integration with other components (Element Locator Engine,
Predictive Testing Engine, RPA Orchestrator, etc.).

Endpoints
---------
POST /api/v1/heal          — Heal a single ELR input (returns output JSON)
POST /api/v1/heal/batch    — Heal multiple ELR inputs in one call
GET  /api/v1/health        — Health check & version info

Usage
-----
    uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload

Or run directly:
    python -m src.api.app
"""

import logging
import time
import traceback
from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from src.runner.heal import heal_from_dict

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("healing_api")

# In-memory latest event for dashboard polling.
LATEST_HEAL_EVENT: dict[str, Any] | None = None

# ──────────────────────────────────────────────
# App
# ──────────────────────────────────────────────
API_VERSION = "1.0.0"

app = FastAPI(
    title="Code Healing Engine API",
    description=(
        "REST API for the AI-Enhanced Self-Healing RPA Framework. "
        "Accepts ELR (Element Locator Report) JSON input, runs the "
        "healing engine, and returns the healing output as JSON."
    ),
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow all origins for research/dev; restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
# Pydantic Models (for validation & docs)
# ──────────────────────────────────────────────
class Metadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    bot_id: str = Field(default="", description="Unique bot identifier, e.g. BOT-ECOMMERCE-01")
    run_id: str = Field(default="", description="Run identifier")
    report_id: str = Field(default="", description="ELR report identifier")
    schema_version: str = Field(default="1.0", description="Input schema version")
    timestamp: str = Field(default="", description="ISO 8601 timestamp")
    source_component: str = Field(default="element_locator_engine")
    target_component: str = Field(default="code_healing_engine")
    environment: str = Field(default="")


class FailureContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    script_path: str | None = Field(default="", description="Path to the broken RPA script")
    failing_line: int | None = Field(default=1, description="Line number that failed")
    action: str = Field(..., description="Playwright action: click, fill, goto, etc.")
    old_locator: str = Field(..., description="The broken CSS/XPath selector")
    error_type: str = Field(..., description="ELEMENT_NOT_FOUND, TIMEOUT, etc.")
    error_message: str = Field(default="", description="Full error text")


class DomContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    new_element_html: str = Field(..., description="Current DOM snippet of the target element")
    page_url: str = Field(default="", description="URL where failure occurred")
    page_name: str | None = Field(default="", description="Friendly page label")


class ElementExpectation(BaseModel):
    model_config = ConfigDict(extra="allow")

    expected_role: str = Field(default="", description="Semantic role: button, link, input, etc.")
    expected_text: str = Field(default="", description="Visible text of element")


class ElementCandidate(BaseModel):
    model_config = ConfigDict(extra="allow")

    css: str | None = Field(default=None, description="CSS selector hint")
    xpath: str | None = Field(default=None, description="XPath hint")
    full_xpath: str | None = Field(default=None, description="Absolute XPath hint")
    score: float | None = Field(default=None, description="Upstream confidence score")
    strategy: str | None = Field(default=None, description="How upstream found this")


class ELRInput(BaseModel):
    """ELR (Element Locator Report) input — the contract between components."""
    model_config = ConfigDict(extra="allow")

    metadata: Metadata
    failure_context: FailureContext
    dom_context: DomContext
    element_expectation: ElementExpectation | None = None
    element_candidate: ElementCandidate | None = None


class HealResponse(BaseModel):
    """Healing engine output."""
    model_config = ConfigDict(extra="allow")

    metadata: dict
    failure_context: dict
    dom_context: dict
    element_expectation: dict | None = None
    element_candidate: dict | None = None
    healing_summary: dict
    script_output: dict
    model_info: dict


class BatchRequest(BaseModel):
    """Batch healing request — list of ELR inputs."""
    inputs: list[ELRInput] = Field(..., description="List of ELR input payloads")


class BatchResponse(BaseModel):
    """Batch healing response."""
    total: int
    success: int
    no_fix: int
    failed: int
    results: list[dict]


class HealthResponse(BaseModel):
    status: str
    version: str
    component: str


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────
@app.get(
    "/api/v1/health",
    response_model=HealthResponse,
    summary="Health Check",
    tags=["System"],
)
async def health_check():
    """Returns API health status and version info."""
    return HealthResponse(
        status="ok",
        version=API_VERSION,
        component="code_healing_engine",
    )


@app.get(
    "/api/v1/heal/latest",
    summary="Get Latest Healing Event",
    tags=["Healing"],
)
async def heal_latest():
    """Returns the most recent /api/v1/heal request + result for live dashboards."""
    if LATEST_HEAL_EVENT is None:
        return {"available": False}
    return {"available": True, **LATEST_HEAL_EVENT}


@app.post(
    "/api/v1/heal",
    response_model=HealResponse,
    summary="Heal Single ELR Input",
    tags=["Healing"],
)
async def heal_single(elr_input: ELRInput):
    """
    Accepts a single ELR JSON input, runs the healing engine,
    and returns the full healing output as the response.

    The engine will:
    1. Predict the best healing strategy using the ML model
    2. Generate locator candidates from the DOM snippet
    3. Merge upstream `element_candidate` if provided
    4. Apply confidence-aware healing gates
    5. Patch the broken script with the new locator
    6. Validate the healed script
    """
    start = time.time()

    try:
        global LATEST_HEAL_EVENT

        # Convert Pydantic model → plain dict for the engine
        inp_dict = elr_input.model_dump(exclude_none=False)

        # Sanitize: replace None sub-objects with {} so downstream .get() calls work
        for key in ("metadata", "failure_context", "dom_context", "element_expectation"):
            if inp_dict.get(key) is None:
                inp_dict[key] = {}

        # Normalize nullable leaf fields from upstream ELR payloads.
        fc = inp_dict.get("failure_context", {})
        dc = inp_dict.get("dom_context", {})
        md = inp_dict.get("metadata", {})
        if fc.get("script_path") is None:
            fc["script_path"] = ""
        if fc.get("failing_line") is None:
            fc["failing_line"] = 1
        if dc.get("page_name") is None:
            dc["page_name"] = ""
        if md.get("bot_id") is None:
            md["bot_id"] = ""

        # Handle element_candidate: strip None-valued fields, collapse to None if empty
        if inp_dict.get("element_candidate") is not None:
            inp_dict["element_candidate"] = {
                k: v for k, v in inp_dict["element_candidate"].items() if v is not None
            }
            if not inp_dict["element_candidate"]:
                inp_dict["element_candidate"] = None

        logger.info(
            "▶ /api/v1/heal  bot_id=%s  error=%s  action=%s",
            inp_dict.get("metadata", {}).get("bot_id", "?"),
            inp_dict.get("failure_context", {}).get("error_type", "?"),
            inp_dict.get("failure_context", {}).get("action", "?"),
        )

        # Run healing engine (persist=True to also save files on disk)
        result = heal_from_dict(inp_dict, persist=True)

        elapsed = time.time() - start
        logger.info(
            "✔ Healed in %.2fs  status=%s  confidence=%.4f  new_locator=%s",
            elapsed,
            result.get("healing_summary", {}).get("status"),
            result.get("healing_summary", {}).get("confidence", 0),
            result.get("healing_summary", {}).get("new_locator", ""),
        )

        LATEST_HEAL_EVENT = {
            "timestamp": time.time(),
            "request": inp_dict,
            "response": result,
        }

        return result

    except Exception as exc:
        logger.error("✖ Healing failed: %s\n%s", exc, traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "HEALING_ENGINE_ERROR",
                "message": str(exc),
            },
        )


@app.post(
    "/api/v1/heal/batch",
    response_model=BatchResponse,
    summary="Heal Multiple ELR Inputs (Batch)",
    tags=["Healing"],
)
async def heal_batch(batch: BatchRequest):
    """
    Accepts a list of ELR inputs and heals them sequentially.
    Returns aggregated results with per-item outputs.
    """
    start = time.time()
    results: list[dict] = []
    counts = {"SUCCESS": 0, "NO_FIX": 0, "FAILED": 0}

    logger.info("▶ /api/v1/heal/batch  count=%d", len(batch.inputs))

    for i, elr_input in enumerate(batch.inputs):
        try:
            inp_dict = elr_input.model_dump(exclude_none=False)

            # Sanitize None sub-objects
            for key in ("metadata", "failure_context", "dom_context", "element_expectation"):
                if inp_dict.get(key) is None:
                    inp_dict[key] = {}

            fc = inp_dict.get("failure_context", {})
            dc = inp_dict.get("dom_context", {})
            md = inp_dict.get("metadata", {})
            if fc.get("script_path") is None:
                fc["script_path"] = ""
            if fc.get("failing_line") is None:
                fc["failing_line"] = 1
            if dc.get("page_name") is None:
                dc["page_name"] = ""
            if md.get("bot_id") is None:
                md["bot_id"] = ""

            if inp_dict.get("element_candidate") is not None:
                inp_dict["element_candidate"] = {
                    k: v for k, v in inp_dict["element_candidate"].items() if v is not None
                }
                if not inp_dict["element_candidate"]:
                    inp_dict["element_candidate"] = None

            result = heal_from_dict(inp_dict, persist=True)
            s = result.get("healing_summary", {}).get("status", "FAILED")
            counts[s] = counts.get(s, 0) + 1
            results.append(result)

        except Exception as exc:
            logger.error("✖ Batch item %d failed: %s", i, exc)
            counts["FAILED"] += 1
            results.append({
                "error": str(exc),
                "healing_summary": {"status": "FAILED"},
                "metadata": elr_input.metadata.model_dump() if elr_input.metadata else {},
            })

    elapsed = time.time() - start
    logger.info(
        "✔ Batch done in %.2fs  total=%d  SUCCESS=%d  NO_FIX=%d  FAILED=%d",
        elapsed, len(batch.inputs), counts["SUCCESS"], counts["NO_FIX"], counts["FAILED"],
    )

    return BatchResponse(
        total=len(batch.inputs),
        success=counts["SUCCESS"],
        no_fix=counts["NO_FIX"],
        failed=counts["FAILED"],
        results=results,
    )


# ──────────────────────────────────────────────
# Run directly: python -m src.api.app
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Code Healing Engine API on http://0.0.0.0:8000")
    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
