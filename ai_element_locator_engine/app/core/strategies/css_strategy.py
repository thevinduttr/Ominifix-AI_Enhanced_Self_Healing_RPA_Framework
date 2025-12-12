"""
app.core.strategies.css_strategy

Strategy that reuses the original CSS locator (if any). It is mainly a
placeholder in this starter implementation, because we are not executing
CSS selectors directly on lxml. In practice you would delegate to the
browser automation layer to evaluate CSS.
"""

from __future__ import annotations

from typing import List

from app.core.models.contracts import FailureFromOrchestrator
from app.core.models.internal import DomSnapshot, ElementCandidateInternal
from app.core.strategies.base import LocatorStrategy


class CssStrategy(LocatorStrategy):
    name = "css_original"

    def find_candidates(
        self,
        dom: DomSnapshot,
        failure: FailureFromOrchestrator,
    ) -> List[ElementCandidateInternal]:
        """
        For the initial version we treat CSS as a hint only and do not attempt
        to evaluate it on the HTML snapshot. When you later integrate a
        Playwright/Selenium bridge, this strategy can call into that bridge
        to resolve the CSS selector on the live browser DOM.
        """
        candidates: List[ElementCandidateInternal] = []

        if not failure.old_locator or failure.old_locator_type != "css":
            return candidates

        # Without a real CSS query engine backed by a browser, we cannot know
        # the exact node. We therefore return no candidates here. The presence
        # of this strategy is primarily for documentation and future work.
        return candidates
