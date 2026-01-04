"""
app.core.strategies.base

Defines the Strategy interface used by all element locator strategies.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from app.core.models.contracts import FailureFromOrchestrator
from app.core.models.internal import DomSnapshot, ElementCandidateInternal


class LocatorStrategy(ABC):
    """
    Base class for all locator strategies.

    Each strategy receives:
    - a DomSnapshot (parsed DOM)
    - the original failure payload for context

    and returns a list of internal candidate elements.
    """

    name: str

    @abstractmethod
    def find_candidates(
        self,
        dom: DomSnapshot,
        failure: FailureFromOrchestrator,
    ) -> List[ElementCandidateInternal]:
        raise NotImplementedError
