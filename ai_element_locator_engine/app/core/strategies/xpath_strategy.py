"""
app.core.strategies.xpath_strategy

Basic strategy that attempts to reuse or slightly relax the original XPath
provided by the failing script. This is particularly useful when only small
changes occurred in the DOM structure.
"""

from __future__ import annotations

import logging
from typing import List

from lxml import etree

from app.core.models.contracts import FailureFromOrchestrator
from app.core.models.internal import DomSnapshot, ElementCandidateInternal
from app.core.dom_parser import build_simple_css_selector
from app.core.strategies.base import LocatorStrategy

logger = logging.getLogger(__name__)


class XPathStrategy(LocatorStrategy):
    name = "xpath_original"

    def find_candidates(
        self,
        dom: DomSnapshot,
        failure: FailureFromOrchestrator,
    ) -> List[ElementCandidateInternal]:
        candidates: List[ElementCandidateInternal] = []

        if not failure.old_locator or failure.old_locator_type != "xpath":
            return candidates

        root = dom.root
        xpath_expr = failure.old_locator

        try:
            matches = root.xpath(xpath_expr)
        except etree.XPathError as exc:
            logger.warning("Invalid original XPath '%s': %s", xpath_expr, exc)
            matches = []

        for node in matches:
            css = build_simple_css_selector(node)
            candidates.append(
                ElementCandidateInternal(
                    node=node,
                    xpath=xpath_expr,
                    css=css,
                    strategy=self.name,
                    heuristic_score=0.8,  # high base score if original still works
                    features={"origin": 1.0},
                )
            )

        return candidates
