"""
app.core.models.contracts

Pydantic models that define the public IO contracts of the Element Locator
Engine. These models should be considered stable and versioned, because other
microservices (Orchestrator, Code Healing, PTQF) depend on them.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field


class FailureFromOrchestrator(BaseModel):
    """
    Input message sent by the Orchestrator when an RPA bot fails due to an
    element-locating issue. This model intentionally focuses on metadata
    required by the locator engine; additional fields can be added as needed.
    """

    page_url: str = Field(..., description="URL of the page where failure occurred")
    failure_type: str = Field(..., description="High-level failure type, e.g. ELEMENT_NOT_FOUND")
    failed_action: str = Field(..., description="Action performed by the bot, e.g. click/fill")
    element_role: Optional[str] = Field(
        None, description="Semantic role of the element, e.g. primary_action, search_box"
    )
    expected_text: Optional[str] = Field(
        None, description="Expected visible text of the element, e.g. 'Login'"
    )
    old_locator: Optional[str] = Field(
        None, description="XPath or CSS selector used by the failing script"
    )
    old_locator_type: Optional[str] = Field(
        None, description="Type of the old locator: 'xpath' or 'css'"
    )
    error_message: Optional[str] = Field(
        None, description="Raw error raised by the RPA runtime"
    )

    # Optional fields to support offline/HTTP based DOM fetching
    page_html: Optional[str] = Field(
        None,
        description=(
            "Optional HTML snapshot of the failed page. "
            "If provided, DOM fetcher does not need to reload the page."
        ),
    )
    screenshot_path: Optional[str] = Field(
        None,
        description="Optional path (or URI) to a screenshot captured at failure time.",
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional orchestration metadata (bot_id, workflow_step, etc.).",
    )


class ReportMetadata(BaseModel):
    report_id: str
    run_id: str
    timestamp: datetime
    source_component: str
    target_component: str


class FailureContext(BaseModel):
    script_path: Optional[str] = None
    failing_line: Optional[int] = None
    action: Optional[str] = None
    old_locator: Optional[str] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None


class DomContext(BaseModel):
    page_url: str
    page_name: Optional[str] = None
    new_element_html: Optional[str] = None


class ElementExpectation(BaseModel):
    expected_role: Optional[str] = None
    expected_text: Optional[str] = None


class ElementCandidate(BaseModel):
    """
    Public representation of a single candidate element chosen by the locator
    engine. This is intentionally compact but includes enough information for
    downstream code generators and test frameworks.
    """

    xpath: Optional[str] = None
    full_xpath: Optional[str] = None
    css: Optional[str] = None
    score: float = Field(..., ge=0.0, le=1.0)
    strategy: str
    extra: Dict[str, Any] = Field(default_factory=dict)


class LocatorEngineReport(BaseModel):
    """
    Main payload returned by the locator engine service.
    """

    metadata: ReportMetadata
    failure_context: FailureContext
    dom_context: DomContext
    element_expectation: ElementExpectation
    element_candidate: Optional[ElementCandidate] = None
