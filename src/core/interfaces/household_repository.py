"""
Household repository interface.
A household groups one or more users and owns the shared inventory + recipes.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Household:
    id: str
    name: str


class IHouseholdRepository(ABC):
    """Interface for household data access operations."""

    @abstractmethod
    def create(self, name: str) -> Household:
        """Create a new household with a generated ID."""
        pass

    @abstractmethod
    def find_by_id(self, household_id: str) -> Optional[Household]:
        """Find a household by ID."""
        pass

    @abstractmethod
    def list_member_ids(self, household_id: str) -> List[str]:
        """List user IDs belonging to a household."""
        pass
