"""
Food log repository interface.

A FoodLogEntry is either:
- a tick on a planned meal (meal_plan_entry_id set, description None), or
- an off-plan entry (meal_plan_entry_id None, description required).

Calories are denormalized at log time so historical totals don't shift if a
recipe's calories_per_serving is later edited.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import List, Optional


@dataclass
class FoodLogEntry:
    id: str
    user_id: str
    log_date: date
    calories: int
    meal_plan_entry_id: Optional[str] = None  # None for off-plan
    description: Optional[str] = None         # required for off-plan


class IFoodLogRepository(ABC):

    @abstractmethod
    def log_planned_meal(self,
                         user_id: str,
                         meal_plan_entry_id: str,
                         log_date: date,
                         calories: int) -> FoodLogEntry:
        """Record that the user ate a planned meal. Idempotent: if the slot
        is already logged for this user, returns the existing entry."""
        pass

    @abstractmethod
    def log_off_plan(self,
                     user_id: str,
                     log_date: date,
                     description: str,
                     calories: int) -> FoodLogEntry:
        """Record an off-plan food entry. Multiple per day allowed."""
        pass

    @abstractmethod
    def find_by_date(self, user_id: str, log_date: date) -> List[FoodLogEntry]:
        """Return all of the user's log entries for a given date."""
        pass

    @abstractmethod
    def delete(self, entry_id: str, user_id: str) -> bool:
        """Remove a log entry. Returns True if a row was removed."""
        pass
