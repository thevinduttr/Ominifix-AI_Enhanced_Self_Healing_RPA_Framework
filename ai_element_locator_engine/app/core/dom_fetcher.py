"""
app.core.dom_fetcher

Responsible for obtaining the HTML snapshot for a failed page. In a full RPA
environment this would talk to Playwright/Selenium or the RPA bot runtime to
retrieve the exact DOM at failure time. For now we support two modes:

1) If the FailureFromOrchestrator already provides `page_html`, we use it.
2) Otherwise we perform a simple HTTP GET using the `page_url`.
"""

from __future__ import annotations

import logging
from typing import Optional

import requests

from app.core.models.contracts import FailureFromOrchestrator
from app.core.dom_parser import parse_html
from app.core.models.internal import DomSnapshot

logger = logging.getLogger(__name__)


def fetch_dom_snapshot(failure: FailureFromOrchestrator) -> Optional[DomSnapshot]:
    """
    Obtain a DomSnapshot for the given failure description.
    Returns None if HTML cannot be obtained.
    """
    if failure.page_html:
        logger.info("Using page_html provided in failure payload")
        return parse_html(failure.page_html, failure.page_url)

    logger.info("Fetching HTML via HTTP GET for url=%s", failure.page_url)
    try:
        resp = requests.get(failure.page_url, timeout=10)
        resp.raise_for_status()
    except Exception as exc:  # broad catch is fine at the boundary
        logger.error("Failed to fetch page_html: %s", exc)
        return None

    return parse_html(resp.text, failure.page_url)
