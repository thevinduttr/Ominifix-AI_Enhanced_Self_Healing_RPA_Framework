"""
app.core.models.internal

Internal domain models used only inside the locator engine implementation.
These wrap lower-level HTML nodes and intermediate scoring fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from lxml.html import HtmlElement


@dataclass
class DomSnapshot:
    """
    Wrapper for a parsed DOM tree. We keep a reference to the lxml root so that
    both XPath and structural operations can be performed.
    """
    root: HtmlElement
    page_url: str
    page_name: str | None = None


@dataclass
class ElementCandidateInternal:
    """
    Internal representation of a candidate DOM node before it is converted into
    the public ElementCandidate Pydantic model. This structure can store rich
    metadata and intermediate scores from different strategies.
    """
    node: HtmlElement
    xpath: str
    css: str | None
    strategy: str
    heuristic_score: float = 0.0
    features: Dict[str, float] = field(default_factory=dict)

    # Final combined score (e.g. after ML model). This will ultimately be used
    # as the 'score' field in the public contract.
    final_score: float = 0.0

    def to_public_dict(self) -> Dict[str, Any]:
        """
        Convert this internal candidate into a dict structure suitable for
        Pydantic ElementCandidate creation.
        """
        from lxml import etree

        full_xpath = etree.ElementTree(self.node).getpath(self.node)

        return {
            "xpath": self.xpath,
            "full_xpath": full_xpath,
            "css": self.css,
            "score": self.final_score,
            "strategy": self.strategy,
            "extra": self.features,
        }
