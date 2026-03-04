"""
app.core.locator_engine

High-level orchestrator for the AI-Powered Element Locator Engine. This class
coordinates DOM fetching, execution of multiple locator strategies, scoring,
and construction of the final LocatorEngineReport.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import List, Optional

from app.core.dom_fetcher import fetch_dom_snapshot
from app.core.models.contracts import (
    FailureFromOrchestrator,
    LocatorEngineReport,
    ReportMetadata,
    FailureContext,
    DomContext,
    ElementExpectation,
    ElementCandidate,
)
from app.core.models.internal import DomSnapshot, ElementCandidateInternal
from app.core.scoring.reliability_model import ReliabilityModel
from app.core.strategies.attribute_strategy import AttributeStrategy
from app.core.strategies.xpath_strategy import XPathStrategy
from app.core.strategies.css_strategy import CssStrategy
from app.core.strategies.fuzzy_dom_strategy import FuzzyDomStrategy
from app.core.strategies.vision_strategy import VisionStrategy
from app.core.strategies.base import LocatorStrategy
from app.infra.settings import settings

logger = logging.getLogger(__name__)


class ElementLocatorEngine:
    """
    Public facade used by the API layer. One instance can be reused for all
    incoming requests because the internal components are stateless.
    """

    def __init__(self) -> None:
        self.strategies: List[LocatorStrategy] = [
            XPathStrategy(),
            CssStrategy(),
            AttributeStrategy(),
            FuzzyDomStrategy(),
            VisionStrategy(),
        ]
        self.reliability_model = ReliabilityModel()

    # --------------------- Public entrypoint --------------------- #

    def locate_and_build_report(
        self, failure: FailureFromOrchestrator
    ) -> LocatorEngineReport:
        """
        Main entrypoint called by the FastAPI route.

        1. Obtain DOM snapshot (optional).
        2. Execute all configured strategies (Vision can run without DOM).
        3. Score and rank candidates.
        4. Apply confidence thresholds.
        5. Build LocatorEngineReport.
        """
        logger.info("Received failure event for url=%s", failure.page_url)

        dom: Optional[DomSnapshot] = fetch_dom_snapshot(failure)

        if dom is None:
            logger.warning(
                "DOM snapshot could not be retrieved; continuing with non-DOM strategies (e.g., vision)."
            )

        candidates = self._run_strategies(dom, failure)

        if candidates:
            self.reliability_model.score_candidates(candidates)

        best_candidate = self._select_best_candidate(candidates)

        return self._build_report(failure, best_candidate)

    # --------------------- Internal helpers --------------------- #

    def _run_strategies(
        self, 
        dom: Optional[DomSnapshot],
        failure: FailureFromOrchestrator,
    ) -> List[ElementCandidateInternal]:
        all_candidates: List[ElementCandidateInternal] = []

        for strategy in self.strategies:
            # Skip DOM-required strategies when dom is not available
            if dom is None and getattr(strategy, "requires_dom", True):
                logger.info(
                    "Skipping strategy %s because dom=None and requires_dom=True",
                    strategy.name,
                )
                continue
            
            try:
                candidates = strategy.find_candidates(dom, failure)
                logger.info(
                    "Strategy %s produced %d candidate(s)", strategy.name, len(candidates)
                )
                all_candidates.extend(candidates)
            except Exception as exc:
                logger.exception("Strategy %s failed: %s", strategy.name, exc)

        # De-duplicate by XPath + strategy as a simple approach
        unique: dict[tuple[str, str], ElementCandidateInternal] = {}
        for c in all_candidates:
            key = (c.xpath, c.strategy)
            if key not in unique:
                unique[key] = c

        return list(unique.values())

    def _select_best_candidate(
        self, candidates: List[ElementCandidateInternal]
    ) -> ElementCandidateInternal | None:
        if not candidates:
            logger.warning("No candidates produced by any strategy")
            return None

        candidates.sort(key=lambda c: c.final_score, reverse=True)
        best = candidates[0]

        logger.info(
            "Best candidate chosen by strategy=%s with score=%.3f",
            best.strategy,
            best.final_score,
        )

        # Apply confidence thresholds gate
        if best.final_score < settings.LOW_CONFIDENCE_THRESHOLD:
            logger.warning(
                "Best candidate score %.3f below low threshold %.3f – "
                "treating as 'no reliable candidate'.",
                best.final_score,
                settings.LOW_CONFIDENCE_THRESHOLD,
            )
            return None

        return best

    def _build_report(
        self,
        failure: FailureFromOrchestrator,
        best_candidate: ElementCandidateInternal | None,
    ) -> LocatorEngineReport:
        """
        Construct a LocatorEngineReport object that will be serialised back to
        the caller by FastAPI. This method is intentionally simple so that
        you can extend it easily when your thesis requirements grow.
        """
        report_id = f"ELR-{uuid.uuid4()}"
        run_id = failure.metadata.get("run_id", f"RUN-{uuid.uuid4()}")

        metadata = ReportMetadata(
            report_id=report_id,
            run_id=run_id,
            timestamp=datetime.utcnow(),
            source_component=settings.SERVICE_NAME,
            target_component="code_healing_engine",  # logical consumer
        )

        failure_ctx = FailureContext(
            script_path=failure.metadata.get("script_path"),
            failing_line=failure.metadata.get("failing_line"),
            action=failure.failed_action,
            old_locator=failure.old_locator,
            error_type=failure.failure_type,
            error_message=failure.error_message,
        )

        dom_ctx = DomContext(
            page_url=failure.page_url,
            page_name=failure.metadata.get("page_name"),
            new_element_html=None,
        )

        expectation = ElementExpectation(
            expected_role=failure.element_role,
            expected_text=failure.expected_text,
        )

        public_candidate: ElementCandidate | None = None

        if best_candidate is not None:
            # Only try to serialize node HTML if it looks like a real lxml element
            try:
                from lxml import etree

                dom_ctx.new_element_html = etree.tostring(
                    best_candidate.node, encoding="unicode"
                )
            except Exception:
                dom_ctx.new_element_html = None

            public_candidate = ElementCandidate(**best_candidate.to_public_dict())

        report = LocatorEngineReport(
            metadata=metadata,
            failure_context=failure_ctx,
            dom_context=dom_ctx,
            element_expectation=expectation,
            element_candidate=public_candidate,
        )

        logger.info("LocatorEngineReport built: report_id=%s", metadata.report_id)
        return report
