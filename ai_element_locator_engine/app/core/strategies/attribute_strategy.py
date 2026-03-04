"""
app.core.strategies.attribute_strategy

Strategy that searches for elements whose attributes and visible text closely
match the expectations derived from the failure payload (old locator, expected
text, semantic role, etc.).
"""

from __future__ import annotations

import logging
from typing import List, Optional

from lxml import etree

from app.core.dom_parser import get_visible_text, build_simple_css_selector
from app.core.models.contracts import FailureFromOrchestrator
from app.core.models.internal import DomSnapshot, ElementCandidateInternal
from app.core.strategies.base import LocatorStrategy

logger = logging.getLogger(__name__)


def _string_similarity(a: str, b: str) -> float:
    """
    Very small utility to compute normalised similarity between two strings.
    This is intentionally simple (character-level Jaccard) to avoid additional
    dependencies; you can replace it with more advanced metrics later.
    """
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0

    set_a, set_b = set(a.lower()), set(b.lower())
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union else 0.0


class AttributeStrategy(LocatorStrategy):
    name = "attribute_text_similarity"

    def find_candidates(
        self,
        dom: DomSnapshot,
        failure: FailureFromOrchestrator,
    ) -> List[ElementCandidateInternal]:
        root: etree._Element = dom.root
        candidates: List[ElementCandidateInternal] = []

        if dom is None:
            return candidates

        root: etree._Element = dom.root

        expected_text = (failure.expected_text or "").strip()
        old_locator_hint = (failure.old_locator or "").strip()

        # Traverse all elements in the DOM. For real-world large pages you might
        # want to restrict this to clickable tags (button, a, input, etc.).
        for node in root.iter():
            tag = node.tag.lower()
            if not isinstance(tag, str):
                continue

            tag = tag.lower()

            # Consider only interactive-like elements as a first filter.
            if tag not in ("button", "a", "input", "div", "span"):
                continue

            text = get_visible_text(node)
            id_attr = node.get("id", "")
            name_attr = node.get("name", "")
            # class_attr = node.get("class", "")
            # placeholder = node.get("placeholder", "")
            # aria_label = node.get("aria-label", "")

            text_sim = _string_similarity(expected_text, text) if expected_text else 0.0

            # The old locator string is often an XPath, so ID similarity is weak by design,
            # but we keep it for scoring features.
            id_sim = _string_similarity(old_locator_hint, id_attr) if id_attr else 0.0
            name_sim = _string_similarity(old_locator_hint, name_attr) if name_attr else 0.0

            # Simple heuristic score composed of multiple aspects.
            heuristic = max(text_sim, id_sim, name_sim)

            if heuristic < 0.2:
                # Ignore very weak matches to keep candidate set small.
                continue

            features = {
                "text_similarity": text_sim,
                "id_similarity": id_sim,
                "name_similarity": name_sim,
            }

            xpath = root.getroottree().getpath(node)
            css = build_simple_css_selector(node)

            candidates.append(
                ElementCandidateInternal(
                    node=node,
                    xpath=xpath,
                    css=css,
                    strategy=self.name,
                    heuristic_score=float(heuristic),
                    features=features,
                )
            )

        # Sort descending by heuristic score; later the ML model will re-rank.
        candidates.sort(key=lambda c: c.heuristic_score, reverse=True)
        return candidates
