"""
app.core.strategies.base

Defines the Strategy interface used by all element locator strategies.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from app.core.models.contracts import FailureFromOrchestrator
from app.core.models.internal import DomSnapshot, ElementCandidateInternal


class LocatorStrategy(ABC):
    """
    Base class for all locator strategies.

    Each strategy receives:
    - an Optional DomSnapshot (parsed DOM). Some strategies (Vision) can operate without DOM.
    - the original failure payload for context

    and returns a list of internal candidate elements.
    """

    name: str

    # If True, strategy requires DOM and will be skipped when dom=None.
    # VisionStrategy should set this to False.
    requires_dom: bool = True

    @abstractmethod
    def find_candidates(
        self,
        dom: Optional[DomSnapshot],
        failure: FailureFromOrchestrator,
    ) -> List[ElementCandidateInternal]:
        raise NotImplementedError
