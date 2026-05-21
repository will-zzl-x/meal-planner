"""Cycle repository interface.

A cycle is a named date range that a household plans meals around.
Only one cycle per household can be 'active' at a time; when the planner
starts a new cycle, the previous one is automatically archived.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import List, Optional


@dataclass
class Cycle:
    id: str
    household_id: str
    start_date: date
    end_date: date
    status: str  # 'active' | 'archived'

    @property
    def label(self) -> str:
        """Short human-readable label, e.g. 'May 21 – May 27'."""
        if self.start_date.year == self.end_date.year:
            return (
                f"{self.start_date.strftime('%b %d')} – "
                f"{self.end_date.strftime('%b %d, %Y')}"
            )
        return (
            f"{self.start_date.strftime('%b %d, %Y')} – "
            f"{self.end_date.strftime('%b %d, %Y')}"
        )

    @property
    def length_days(self) -> int:
        return (self.end_date - self.start_date).days + 1


class ICycleRepository(ABC):

    @abstractmethod
    def create(self, household_id: str, start_date: date, end_date: date) -> "Cycle":
        """Create a new active cycle, archiving any existing active cycle."""

    @abstractmethod
    def find_active(self, household_id: str) -> Optional["Cycle"]:
        """Return the current active cycle, or None if none exists."""

    @abstractmethod
    def find_all(self, household_id: str) -> List["Cycle"]:
        """Return all cycles for the household, newest first."""

    @abstractmethod
    def archive(self, cycle_id: str, household_id: str) -> bool:
        """Mark a cycle as archived. Returns True if a row was changed."""
