"""
Calorie Banking Service - Weekly Distribution and Banking Logic
Clean Architecture - Business Logic Layer
"""
from decimal import Decimal
from typing import List, Dict, Optional
from datetime import date, timedelta
from dataclasses import dataclass

@dataclass
class DailyCalorieTarget:
    """Daily calorie target with banking information."""
    date: date
    base_target: int
    banked_calories: int
    borrowed_calories: int
    final_target: int
    is_special_event: bool = False
    event_description: Optional[str] = None

@dataclass
class WeeklyDistribution:
    """Weekly calorie distribution plan."""
    week_start_date: date
    total_weekly_calories: int
    daily_targets: List[DailyCalorieTarget]
    total_banked: int
    total_borrowed: int
    is_balanced: bool

class CalorieBankingService:
    """Service for weekly calorie distribution and banking/borrowing logic."""
    
    def __init__(self, minimum_calories_per_lb: int = 10):
        """
        Initialize calorie banking service.
        
        Args:
            minimum_calories_per_lb: Minimum calories per pound of body weight
        """
        self.minimum_calories_per_lb = minimum_calories_per_lb
    
    def create_weekly_distribution(self, weekly_calorie_target: int, 
                                 user_weight: Decimal,
                                 special_events: Optional[Dict[date, str]] = None,
                                 preferred_distribution: Optional[List[int]] = None) -> WeeklyDistribution:
        """
        Create weekly calorie distribution with banking support.
        
        Args:
            weekly_calorie_target: Total calories for the week
            user_weight: User's current weight for minimum calculation
            special_events: Dict of date -> event description
            preferred_distribution: Optional custom daily distribution
            
        Returns:
            Weekly distribution plan with banking
        """
        week_start = date.today() - timedelta(days=date.today().weekday())
        minimum_daily = int(user_weight * self.minimum_calories_per_lb)
        
        # Default even distribution
        if not preferred_distribution:
            base_daily = weekly_calorie_target // 7
            preferred_distribution = [base_daily] * 7
        
        # Adjust for special events
        if special_events:
            preferred_distribution = self._adjust_for_special_events(
                preferred_distribution, special_events, week_start, minimum_daily
            )
        
        # Create daily targets
        daily_targets = []
        total_banked = 0
        total_borrowed = 0
        
        for i, target in enumerate(preferred_distribution):
            current_date = week_start + timedelta(days=i)
            
            # Calculate banking
            base_target = weekly_calorie_target // 7
            difference = target - base_target
            
            banked = max(0, -difference)  # Positive when under base
            borrowed = max(0, difference)  # Positive when over base
            
            total_banked += banked
            total_borrowed += borrowed
            
            # Check for special events
            is_special = special_events and current_date in special_events
            event_desc = special_events.get(current_date) if special_events else None
            
            daily_targets.append(DailyCalorieTarget(
                date=current_date,
                base_target=base_target,
                banked_calories=banked,
                borrowed_calories=borrowed,
                final_target=target,
                is_special_event=is_special,
                event_description=event_desc
            ))
        
        return WeeklyDistribution(
            week_start_date=week_start,
            total_weekly_calories=weekly_calorie_target,
            daily_targets=daily_targets,
            total_banked=total_banked,
            total_borrowed=total_borrowed,
            is_balanced=(total_banked == total_borrowed)
        )
    
    def _adjust_for_special_events(self, distribution: List[int], 
                                 special_events: Dict[date, str],
                                 week_start: date, 
                                 minimum_daily: int) -> List[int]:
        """
        Adjust distribution for special events by banking calories from other days.
        
        Args:
            distribution: Current daily distribution
            special_events: Special events requiring extra calories
            week_start: Start of the week
            minimum_daily: Minimum calories per day
            
        Returns:
            Adjusted distribution
        """
        adjusted = distribution.copy()
        
        for event_date, description in special_events.items():
            if week_start <= event_date < week_start + timedelta(days=7):
                day_index = (event_date - week_start).days
                
                # Add 500 calories for restaurant/special event
                extra_calories = 500
                adjusted[day_index] += extra_calories
                
                # Remove calories from other days (100 per day from 5 days)
                calories_per_day = extra_calories // 5
                days_to_reduce = [i for i in range(7) if i != day_index][:5]
                
                for day in days_to_reduce:
                    reduction = min(calories_per_day, 
                                  adjusted[day] - minimum_daily)
                    adjusted[day] -= reduction
        
        return adjusted
    
    def calculate_remaining_weekly_calories(self, weekly_target: int,
                                          consumed_so_far: List[int],
                                          days_remaining: int) -> Dict[str, int]:
        """
        Calculate remaining calories for the week and suggest distribution.
        
        Args:
            weekly_target: Total weekly calorie target
            consumed_so_far: Calories consumed each day so far
            days_remaining: Number of days left in the week
            
        Returns:
            Dict with remaining calories and suggested daily amounts
        """
        total_consumed = sum(consumed_so_far)
        remaining_calories = weekly_target - total_consumed
        
        if days_remaining <= 0:
            return {
                "remaining_total": remaining_calories,
                "daily_average": 0,
                "status": "week_complete"
            }
        
        daily_average = remaining_calories // days_remaining
        
        # Determine status
        status = "on_track"
        if remaining_calories < 0:
            status = "over_budget"
        elif daily_average < 1000:
            status = "very_low"
        elif daily_average > 3000:
            status = "very_high"
        
        return {
            "remaining_total": remaining_calories,
            "daily_average": daily_average,
            "days_remaining": days_remaining,
            "status": status
        }
    
    def suggest_calorie_redistribution(self, current_distribution: List[int],
                                     target_change: int,
                                     user_weight: Decimal,
                                     priority_days: Optional[List[int]] = None) -> List[int]:
        """
        Suggest redistribution of calories across the week.
        
        Args:
            current_distribution: Current daily calorie targets
            target_change: Total calories to add/remove from week
            user_weight: User weight for minimum calculations
            priority_days: Days to prioritize for changes (0=Monday, 6=Sunday)
            
        Returns:
            Suggested new distribution
        """
        minimum_daily = int(user_weight * self.minimum_calories_per_lb)
        new_distribution = current_distribution.copy()
        
        # Distribute change across days
        daily_change = target_change // 7
        remaining_change = target_change % 7
        
        # Apply base change to all days
        for i in range(7):
            new_distribution[i] += daily_change
            
            # Ensure minimum is maintained
            if new_distribution[i] < minimum_daily:
                deficit = minimum_daily - new_distribution[i]
                new_distribution[i] = minimum_daily
                remaining_change += deficit
        
        # Distribute remaining change to priority days
        if remaining_change != 0 and priority_days:
            change_per_priority_day = remaining_change // len(priority_days)
            
            for day in priority_days:
                if 0 <= day < 7:
                    new_distribution[day] += change_per_priority_day
                    
                    # Check minimum again
                    if new_distribution[day] < minimum_daily:
                        new_distribution[day] = minimum_daily
        
        return new_distribution
    
    def validate_weekly_distribution(self, distribution: List[int],
                                   weekly_target: int,
                                   user_weight: Decimal) -> Dict[str, any]:
        """
        Validate a weekly calorie distribution.
        
        Args:
            distribution: Daily calorie targets
            weekly_target: Target weekly calories
            user_weight: User weight for validation
            
        Returns:
            Validation results with warnings and suggestions
        """
        minimum_daily = int(user_weight * self.minimum_calories_per_lb)
        
        warnings = []
        total_calories = sum(distribution)
        
        # Check total matches target
        if abs(total_calories - weekly_target) > 50:
            warnings.append(f"Total calories ({total_calories}) don't match target ({weekly_target})")
        
        # Check daily minimums
        for i, daily in enumerate(distribution):
            if daily < minimum_daily:
                day_name = ["Monday", "Tuesday", "Wednesday", "Thursday", 
                           "Friday", "Saturday", "Sunday"][i]
                warnings.append(f"{day_name} below minimum ({daily} < {minimum_daily})")
        
        # Check for extreme variations
        avg_daily = total_calories / 7
        for i, daily in enumerate(distribution):
            variation = abs(daily - avg_daily) / avg_daily
            if variation > 0.5:  # More than 50% variation
                day_name = ["Monday", "Tuesday", "Wednesday", "Thursday", 
                           "Friday", "Saturday", "Sunday"][i]
                warnings.append(f"{day_name} has extreme variation from average")
        
        return {
            "is_valid": len(warnings) == 0,
            "warnings": warnings,
            "total_calories": total_calories,
            "average_daily": int(avg_daily),
            "minimum_daily": minimum_daily
        }
