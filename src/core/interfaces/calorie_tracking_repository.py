"""
Calorie tracking repository interface for flexible dieting features.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass
from decimal import Decimal
from datetime import date

@dataclass
class DailyCalorieLog:
    """Daily calorie and macro tracking log."""
    user_id: str
    date: date
    target_calories: int
    consumed_calories: int
    banked_calories: int
    protein_grams: Optional[Decimal] = None
    carb_grams: Optional[Decimal] = None
    fat_grams: Optional[Decimal] = None

@dataclass
class WeeklyCaloriePlan:
    """Weekly calorie distribution plan."""
    user_id: str
    week_start_date: date
    weekly_calorie_target: int
    daily_targets: List[int]  # 7 days of calorie targets
    special_events: Optional[List[str]] = None  # Restaurant days, etc.

class ICalorieTrackingRepository(ABC):
    """Interface for calorie tracking data access operations."""
    
    @abstractmethod
    def log_daily_calories(self, log: DailyCalorieLog) -> DailyCalorieLog:
        """
        Log daily calorie consumption.
        
        Args:
            log: Daily calorie log entry
            
        Returns:
            Saved log entry
        """
        pass
    
    @abstractmethod
    def get_daily_log(self, user_id: str, date: date) -> Optional[DailyCalorieLog]:
        """
        Get calorie log for a specific date.
        
        Args:
            user_id: ID of the user
            date: Date to retrieve
            
        Returns:
            Daily log if found, None otherwise
        """
        pass
    
    @abstractmethod
    def get_weekly_logs(self, user_id: str, week_start_date: date) -> List[DailyCalorieLog]:
        """
        Get calorie logs for a week.
        
        Args:
            user_id: ID of the user
            week_start_date: Start date of the week
            
        Returns:
            List of daily logs for the week
        """
        pass
    
    @abstractmethod
    def save_weekly_plan(self, plan: WeeklyCaloriePlan) -> WeeklyCaloriePlan:
        """
        Save weekly calorie distribution plan.
        
        Args:
            plan: Weekly calorie plan
            
        Returns:
            Saved weekly plan
        """
        pass
    
    @abstractmethod
    def get_weekly_plan(self, user_id: str, week_start_date: date) -> Optional[WeeklyCaloriePlan]:
        """
        Get weekly calorie plan.
        
        Args:
            user_id: ID of the user
            week_start_date: Start date of the week
            
        Returns:
            Weekly plan if found, None otherwise
        """
        pass
    
    @abstractmethod
    def calculate_banked_calories(self, user_id: str, up_to_date: date) -> Decimal:
        """
        Calculate total banked calories up to a specific date.
        
        Args:
            user_id: ID of the user
            up_to_date: Calculate up to this date
            
        Returns:
            Total banked calories (can be negative if borrowed)
        """
        pass
