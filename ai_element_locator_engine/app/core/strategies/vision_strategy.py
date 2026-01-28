"""
app.core.strategies.vision_strategy

Computer-vision locator recovery using OpenCV template matching (edge-based).

Key requirements satisfied:
- Works with DOM available OR dom=None (vision-only fallback).
- Uses screenshot_path + template_path from FailureFromOrchestrator.
- Computes match confidence via Canny edges + cv2.TM_CCOEFF_NORMED.
- Applies per-template thresholds.
- If DOM exists, converts vision confidence into DOM locator candidates by:
  - filtering interactive tags (button/a/input)
  - matching expected_text (substring match)
- If DOM is missing (page_html not provided and URL unreachable), returns a
  "vision-only" candidate so the pipeline still produces an output for demo.

Notes:
- For DOM-present mode, candidates contain XPath/CSS locators.
- For DOM-missing mode, candidate will include score + vision fields, but
  xpath may be empty. This is acceptable for evaluation and dashboard demo.
- features dict remains numeric-only (Dict[str, float]) to match internal model.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

import cv2
from lxml.html import fromstring

from app.core.dom_parser import build_simple_css_selector
from app.core.models.contracts import FailureFromOrchestrator
from app.core.models.internal import DomSnapshot, ElementCandidateInternal
from app.core.strategies.base import LocatorStrategy

logger = logging.getLogger(__name__)

# Edge parameters
CANNY_LOW = 50
CANNY_HIGH = 150

DEFAULT_THRESHOLD = 0.70
TEMPLATE_THRESHOLDS: Dict[str, float] = {
    "checkbox.png": 0.85,
    "login_button.png": 0.55,
    "dropdown_select.png": 0.65,
    "add_button.png": 0.74,
    "delete.png": 0.78,
}


def _load_edges(path: Path) -> Optional["cv2.Mat"]:
    gray = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if gray is None:
        return None
    return cv2.Canny(gray, CANNY_LOW, CANNY_HIGH)


def _vision_match_score(screenshot_path: Path, template_path: Path) -> Optional[float]:
    """
    Return best template match score in [0,1] using edge-based matching.
    """
    screenshot_edges = _load_edges(screenshot_path)
    template_edges = _load_edges(template_path)

    if screenshot_edges is None:
        logger.warning("VisionStrategy: cannot read screenshot: %s", screenshot_path)
        return None
    if template_edges is None:
        logger.warning("VisionStrategy: cannot read template: %s", template_path)
        return None

    if (
        template_edges.shape[0] > screenshot_edges.shape[0]
        or template_edges.shape[1] > screenshot_edges.shape[1]
    ):
        logger.warning("VisionStrategy: template larger than screenshot")
        return None

    result = cv2.matchTemplate(screenshot_edges, template_edges, cv2.TM_CCOEFF_NORMED)
    _min_val, max_val, _min_loc, _max_loc = cv2.minMaxLoc(result)

    # clamp to [0,1]
    return float(max(0.0, min(1.0, max_val)))


class VisionStrategy(LocatorStrategy):
    """
    OpenCV vision-based strategy.

    This strategy can operate WITHOUT a DOM (dom=None), so it must not be skipped
    when the DOM snapshot cannot be retrieved.
    """

    name = "vision_template_match"
    requires_dom = False

    def find_candidates(
        self,
        dom: Optional[DomSnapshot],
        failure: FailureFromOrchestrator,
    ) -> List[ElementCandidateInternal]:
        # 1) Preconditions
        if not failure.screenshot_path or not failure.template_path:
            logger.info("VisionStrategy: missing screenshot_path/template_path")
            return []

        screenshot_path = Path(failure.screenshot_path)
        template_path = Path(failure.template_path)

        if not screenshot_path.exists():
            logger.warning("VisionStrategy: screenshot file not found: %s", screenshot_path)
            return []
        if not template_path.exists():
            logger.warning("VisionStrategy: template file not found: %s", template_path)
            return []

        # 2) Compute vision match score
        score = _vision_match_score(screenshot_path, template_path)
        if score is None:
            return []

        thr = TEMPLATE_THRESHOLDS.get(template_path.name, DEFAULT_THRESHOLD)
        if score < thr:
            logger.info(
                "VisionStrategy: below threshold score=%.4f thr=%.2f template=%s",
                score,
                thr,
                template_path.name,
            )
            return []

        # Heuristic score in [0.50..1.0]
        heuristic = 0.50 + (0.50 * score)

        # 3) If DOM is missing, return a vision-only candidate (for demo + fallback)
        if dom is None:
            logger.info(
                "VisionStrategy: dom=None, returning vision-only candidate score=%.4f thr=%.2f",
                score,
                thr,
            )

            # minimal node so internal pipeline can still serialize something
            dummy_node = fromstring('<div data-vision="true"></div>')

            return [
                ElementCandidateInternal(
                    node=dummy_node,
                    xpath="",  # not available without DOM
                    css=None,
                    strategy=self.name,
                    heuristic_score=float(heuristic),
                    features={
                        "vision_match_score": float(score),
                        "vision_threshold": float(thr),
                    },
                    final_score=0.0,  # will be set by ML scorer if used
                )
            ]

        # 4) DOM exists: generate DOM candidates that match expected_text
        expected = (failure.expected_text or "").strip().lower()
        if not expected:
            logger.info("VisionStrategy: expected_text missing; returning vision-only candidate (dom available)")
            dummy_node = fromstring('<div data-vision="true"></div>')
            return [
                ElementCandidateInternal(
                    node=dummy_node,
                    xpath="",
                    css=None,
                    strategy=self.name,
                    heuristic_score=float(heuristic),
                    features={
                        "vision_match_score": float(score),
                        "vision_threshold": float(thr),
                    },
                    final_score=0.0,
                )
            ]

        root = dom.root
        tree = root.getroottree()

        candidates: List[ElementCandidateInternal] = []
        allowed_tags = {"button", "a", "input"}

        for node in root.iter():
            # Tag filtering
            tag = getattr(node, "tag", None)
            if not isinstance(tag, str):
                continue
            tag = tag.lower()
            if tag not in allowed_tags:
                continue

            # Text extraction
            node_text = ("".join(node.itertext()) or "").strip().lower()
            if tag == "input" and not node_text:
                node_text = (node.get("value") or "").strip().lower()

            # Substring match for robustness
            if expected not in node_text:
                continue

            xpath = tree.getpath(node)
            css = build_simple_css_selector(node)

            candidates.append(
                ElementCandidateInternal(
                    node=node,
                    xpath=xpath,
                    css=css,
                    strategy=self.name,
                    heuristic_score=float(heuristic),
                    features={
                        "vision_match_score": float(score),
                        "vision_threshold": float(thr),
                    },
                    final_score=0.0,
                )
            )

        candidates.sort(key=lambda c: c.heuristic_score, reverse=True)

        logger.info(
            "VisionStrategy: score=%.4f thr=%.2f dom_candidates=%d",
            score,
            thr,
            len(candidates),
        )

        # If DOM candidates are empty but vision score is strong, still return a vision-only candidate
        if not candidates:
            logger.info(
                "VisionStrategy: vision match strong but no DOM text match; returning vision-only candidate"
            )
            dummy_node = fromstring('<div data-vision="true"></div>')
            return [
                ElementCandidateInternal(
                    node=dummy_node,
                    xpath="",
                    css=None,
                    strategy=self.name,
                    heuristic_score=float(heuristic),
                    features={
                        "vision_match_score": float(score),
                        "vision_threshold": float(thr),
                    },
                    final_score=0.0,
                )
            ]

        return candidates