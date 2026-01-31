"""
Calorie Banking Service for flexible dieting.
Handles weekly calorie distribution, banking/borrowing, and safety limits.
"""
from decimal import Decimal
from typing import List, Dict, Tuple, Optional
from datetime import date, timedelta
from dataclasses import dataclass

@dataclass
class DailyCalorieTarget:
    """Daily calorie target with context."""
    date: date
    target_calories: int
    is_special_day: bool = False
    special_day_type: Optional[str] = None  # "restaurant", "event", etc.

@dataclass
class WeeklyDistribution:
    """Weekly calorie distribution plan."""
    weekly_target: int
    daily_targets: List[DailyCalorieTarget]
    total_banked: int
    safety_warnings: List[str]

class CalorieBankingService:
    """Service for flexible dieting calorie banking and distribution."""
    
    def __init__(self):
        self.min_calories_per_lb = 10  # Minimum 10 calories per pound body weight
        self.max_deficit_per_day = 1000  # Maximum 1000 calorie deficit per day
        self.restaurant_buffer = 100  # Default buffer calories for restaurant days
    
    def distribute_weekly_calories(self, 
                                 weekly_target: int,
                                 body_weight: Decimal,
                                 week_start_date: date,
                                 special_days: Dict[date, str] = None,
                                 restaurant_estimates: Dict[date, int] = None) -> WeeklyDistribution:
        """
        Distribute weekly calories across 7 days with banking logic.
        
        Args:
            weekly_target: Total calories for the week
            body_weight: User's body weight in pounds (for safety calculations)
            week_start_date: Monday of the week
            special_days: Dict of {date: "restaurant"/"event"} for special planning
            restaurant_estimates: Dict of {date: estimated_calories} for known restaurant meals
            
        Returns:
            WeeklyDistribution with daily targets and safety warnings
        """
        if special_days is None:
            special_days = {}
        if restaurant_estimates is None:
            restaurant_estimates = {}
        
        # Calculate safety limits
        min_daily_calories = int(body_weight * self.min_calories_per_lb)
        daily_average = weekly_target // 7
        
        # Initialize daily targets
        daily_targets = []
        safety_warnings = []
        
        # Step 1: Handle special days first
        remaining_calories = weekly_target
        remaining_days = 7
        
        for i in range(7):
            current_date = week_start_date + timedelta(days=i)
            
            if current_date in special_days:
                # Special day handling
                if special_days[current_date] == "restaurant":
                    if current_date in restaurant_estimates:
                        # User provided estimate
                        target = restaurant_estimates[current_date]
                    else:
                        # Default: average + buffer
                        target = daily_average + self.restaurant_buffer
                    
                    daily_targets.append(DailyCalorieTarget(
                        date=current_date,
                        target_calories=target,
                        is_special_day=True,
                        special_day_type="restaurant"
                    ))
                    
                    remaining_calories -= target
                    remaining_days -= 1
        
        # Step 2: Distribute remaining calories across normal days
        if remaining_days > 0:
            avg_remaining = remaining_calories // remaining_days
            
            for i in range(7):
                current_date = week_start_date + timedelta(days=i)
                
                # Skip if already handled as special day
                if current_date in special_days:
                    continue
                
                # Calculate target with banking preparation
                target = avg_remaining
                
                # Prepare for upcoming special days by reducing current day
                upcoming_special = self._get_upcoming_special_days(current_date, special_days, 3)
                if upcoming_special:
                    # Reduce by buffer amount per upcoming special day
                    reduction = min(self.restaurant_buffer * len(upcoming_special), 
                                  target - min_daily_calories)
                    target -= reduction
                
                # Safety check
                if target < min_daily_calories:
                    safety_warnings.append(
                        f"{current_date.strftime('%A')}: Target {target} below minimum {min_daily_calories} calories"
                    )
                    target = min_daily_calories
                
                daily_targets.append(DailyCalorieTarget(
                    date=current_date,
                    target_calories=target,
                    is_special_day=False
                ))
        
        # Sort by date
        daily_targets.sort(key=lambda x: x.date)
        
        # Calculate total banked calories (difference from average distribution)
        total_assigned = sum(dt.target_calories for dt in daily_targets)
        total_banked = weekly_target - total_assigned
        
        return WeeklyDistribution(
            weekly_target=weekly_target,
            daily_targets=daily_targets,
            total_banked=total_banked,
            safety_warnings=safety_warnings
        )
    
    def calculate_banking_impact(self, 
                               consumed_calories: int,
                               target_calories: int,
                               current_banked: int) -> Tuple[int, str]:
        """
        Calculate the banking impact of daily consumption.
        
        Returns:
            (new_banked_amount, description)
        """
        difference = target_calories - consumed_calories
        new_banked = current_banked + difference
        
        if difference > 0:
            description = f"Banked {difference} calories (total: {new_banked})"
        elif difference < 0:
            description = f"Used {abs(difference)} banked calories (remaining: {new_banked})"
        else:
            description = f"Hit target exactly (banked: {new_banked})"
        
        return new_banked, description
    
    def redistribute_for_special_day(self,
                                   current_distribution: WeeklyDistribution,
                                   special_date: date,
                                   estimated_calories: int,
                                   body_weight: Decimal) -> WeeklyDistribution:
        """
        Redistribute calories when user adds a special day (like restaurant).
        
        Args:
            current_distribution: Current weekly distribution
            special_date: Date of the special day
            estimated_calories: Estimated calories for special day
            body_weight: User's body weight for safety calculations
            
        Returns:
            Updated WeeklyDistribution
        """
        min_daily_calories = int(body_weight * self.min_calories_per_lb)
        
        # Find the target for the special date
        special_target = None
        other_targets = []
        
        for target in current_distribution.daily_targets:
            if target.date == special_date:
                special_target = target
            else:
                other_targets.append(target)
        
        if not special_target:
            return current_distribution  # Date not found
        
        # Calculate excess calories needed for special day
        excess_needed = estimated_calories - special_target.target_calories
        
        if excess_needed <= 0:
            # No redistribution needed
            return current_distribution
        
        # Distribute the excess across other days
        days_to_reduce = len(other_targets)
        if days_to_reduce == 0:
            return current_distribution
        
        reduction_per_day = excess_needed // days_to_reduce
        remaining_reduction = excess_needed % days_to_reduce
        
        # Apply reductions with safety checks
        updated_targets = []
        safety_warnings = list(current_distribution.safety_warnings)
        
        for i, target in enumerate(other_targets):
            reduction = reduction_per_day
            if i < remaining_reduction:
                reduction += 1
            
            new_target = target.target_calories - reduction
            
            # Safety check
            if new_target < min_daily_calories:
                safety_warnings.append(
                    f"{target.date.strftime('%A')}: Cannot reduce below {min_daily_calories} calories"
                )
                new_target = min_daily_calories
            
            updated_targets.append(DailyCalorieTarget(
                date=target.date,
                target_calories=new_target,
                is_special_day=target.is_special_day,
                special_day_type=target.special_day_type
            ))
        
        # Add the updated special day
        updated_targets.append(DailyCalorieTarget(
            date=special_date,
            target_calories=estimated_calories,
            is_special_day=True,
            special_day_type="restaurant"
        ))
        
        # Sort by date
        updated_targets.sort(key=lambda x: x.date)
        
        return WeeklyDistribution(
            weekly_target=current_distribution.weekly_target,
            daily_targets=updated_targets,
            total_banked=current_distribution.total_banked,
            safety_warnings=safety_warnings
        )
    
    def _get_upcoming_special_days(self, current_date: date, 
                                 special_days: Dict[date, str], 
                                 look_ahead_days: int) -> List[date]:
        """Get special days within the next N days."""
        upcoming = []
        for i in range(1, look_ahead_days + 1):
            check_date = current_date + timedelta(days=i)
            if check_date in special_days:
                upcoming.append(check_date)
        return upcoming
    
    def validate_weekly_distribution(self, distribution: WeeklyDistribution, 
                                   body_weight: Decimal) -> List[str]:
        """
        Validate that weekly distribution meets safety requirements.
        
        Returns:
            List of validation warnings/errors
        """
        warnings = []
        min_daily = int(body_weight * self.min_calories_per_lb)
        
        for target in distribution.daily_targets:
            if target.target_calories < min_daily:
                warnings.append(
                    f"{target.date.strftime('%A')}: {target.target_calories} calories below minimum {min_daily}"
                )
            
            if target.target_calories > min_daily * 3:  # Reasonable upper limit
                warnings.append(
                    f"{target.date.strftime('%A')}: {target.target_calories} calories very high"
                )
        
        return warnings
