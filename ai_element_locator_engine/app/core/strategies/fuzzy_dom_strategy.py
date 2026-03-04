"""
app.core.strategies.fuzzy_dom_strategy

Strategy that uses structural (DOM tree) similarity to recover elements.
It focuses on the ancestor tag path and depth of nodes, which is useful
when IDs and texts change but layout remains similar.

This complements AttributeStrategy by looking at the *shape* of the DOM
around the original element rather than only its text and attributes.
"""

from __future__ import annotations

from typing import List, Optional

from lxml import etree

from app.core.models.contracts import FailureFromOrchestrator
from app.core.models.internal import DomSnapshot, ElementCandidateInternal
from app.core.dom_parser import build_simple_css_selector
from app.core.strategies.base import LocatorStrategy


def _compute_ancestor_path(node: etree._Element) -> list[str]:
    """
    Return a list of ancestor tag names from root to the node.
    Example: ['html', 'body', 'form', 'button'].
    """
    path: list[str] = []
    current = node
    while current is not None:
        try:
            tag_name = current.tag.lower()
        except AttributeError:
            break
        path.append(tag_name)
        current = current.getparent()
    return list(reversed(path))


def _path_similarity(path_a: list[str], path_b: list[str]) -> float:
    """
    Very simple normalised similarity between two ancestor paths based on
    longest common prefix length.

    If path_a = [html, body, form, button]
    and path_b = [html, body, form, input]
    longest common prefix length = 3 => similarity = 3 / max(4, 4) = 0.75
    """
    if not path_a or not path_b:
        return 0.0

    max_len = min(len(path_a), len(path_b))
    match_len = 0
    for i in range(max_len):
        if path_a[i] == path_b[i]:
            match_len += 1
        else:
            break

    return match_len / max(len(path_a), len(path_b))


class FuzzyDomStrategy(LocatorStrategy):
    name = "fuzzy_dom_structure"
    requires_dom = True

    def find_candidates(
        self,
        dom: Optional[DomSnapshot],
        failure: FailureFromOrchestrator,
    ) -> List[ElementCandidateInternal]:
        root: etree._Element = dom.root
        candidates: List[ElementCandidateInternal] = []

        if dom is None:
            return candidates

        root: etree._Element = dom.root
        
        # If no old XPath, we cannot compute a reference structural path.
        if not failure.old_locator or failure.old_locator_type != "xpath":
            return candidates

        tree = root.getroottree()

        # Try to resolve the original XPath on the *current* DOM.
        # Even if the ID changed, some part of the path might still match.
        try:
            old_matches = root.xpath(failure.old_locator)
        except etree.XPathError:
            old_matches = []

        if not old_matches:
            # No reference node, strategy cannot contribute.
            return candidates

        ref_node = old_matches[0]
        ref_path = _compute_ancestor_path(ref_node)
        ref_depth = len(ref_path)

        for node in root.iter():
            tag = getattr(node, "tag", "")
            if not isinstance(tag, str):
                continue
    
            tag = tag.lower()

            # Focus on likely interactive nodes – avoids scanning every node.
            if tag not in ("button", "a", "input", "div", "span"):
                continue

            path = _compute_ancestor_path(node)
            depth = len(path)
            depth_diff = abs(depth - ref_depth)

            path_sim = _path_similarity(ref_path, path)

            # Penalise large depth differences.
            depth_penalty = max(0.0, 1.0 - depth_diff * 0.1)
            heuristic = path_sim * depth_penalty

            if heuristic < 0.3:
                # Ignore weak structural matches.
                continue

            xpath = tree.getpath(node)
            css = build_simple_css_selector(node)

            candidates.append(
                ElementCandidateInternal(
                    node=node,
                    xpath=xpath,
                    css=css,
                    strategy=self.name,
                    heuristic_score=heuristic,
                    features={
                        "dom_path_similarity": path_sim,
                        "dom_depth_diff": float(depth_diff),
                    },
                )
            )

        candidates.sort(key=lambda c: c.heuristic_score, reverse=True)
        return candidates
