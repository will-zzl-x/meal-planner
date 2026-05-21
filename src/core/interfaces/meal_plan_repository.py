"""
Meal plan repository interface.

A meal plan entry is one recipe planned for one (date, meal_type) slot in a
household. The same recipe can appear multiple times across the week, but
(date, recipe, meal_type) within a household is unique.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import List, Optional


@dataclass
class MealPlanEntry:
    """One planned meal slot. Read paths populate the joined fields
    (recipe_name, calories_per_serving) so the UI doesn't need a second query."""
    id: str
    recipe_id: str
    planned_date: date
    planned_servings: int
    meal_type: str  # breakfast | lunch | dinner | snack
    recipe_name: Optional[str] = None
    calories_per_serving: Optional[int] = None


class IMealPlanRepository(ABC):

    @abstractmethod
    def save_entry(self,
                   household_id: str,
                   recipe_id: str,
                   planned_date: date,
                   planned_servings: int,
                   meal_type: str) -> MealPlanEntry:
        """Insert (or replace) a meal plan entry. Returns the persisted entry."""
        pass

    @abstractmethod
    def find_by_week(self, household_id: str, week_start_date: date) -> List[MealPlanEntry]:
        """Return all entries for the 7-day window starting at week_start_date."""
        pass

    @abstractmethod
    def find_by_date(self, household_id: str, day: date) -> List[MealPlanEntry]:
        """Return entries for a single day, ordered by meal_type."""
        pass

    @abstractmethod
    def delete_entry(self, entry_id: str, household_id: str) -> bool:
        """Delete a single entry. Returns True if a row was removed."""
        pass

    @abstractmethod
    def find_by_date_range(self, household_id: str, start: date, end: date) -> List[MealPlanEntry]:
        """Return entries in the inclusive date range [start, end]."""
        pass

    @abstractmethod
    def clear_week(self, household_id: str, week_start_date: date) -> int:
        """Remove all entries within the 7-day window. Returns the count removed."""
        pass
