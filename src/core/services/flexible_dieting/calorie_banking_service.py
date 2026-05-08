"""
Calorie Banking Service - Weekly Distribution and Banking Logic
Clean Architecture - Business Logic Layer
"""
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from datetime import date, timedelta
from dataclasses import dataclass, field

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

    # Read-only aliases for legacy call sites that used the simpler shape.
    @property
    def target_calories(self) -> int:
        return self.final_target

    @property
    def is_special_day(self) -> bool:
        return self.is_special_event

    @property
    def special_day_type(self) -> Optional[str]:
        return self.event_description

@dataclass
class WeeklyDistribution:
    """Weekly calorie distribution plan."""
    week_start_date: date
    total_weekly_calories: int
    daily_targets: List[DailyCalorieTarget]
    total_banked: int
    total_borrowed: int
    is_balanced: bool
    safety_warnings: List[str] = field(default_factory=list)

    @property
    def weekly_target(self) -> int:
        return self.total_weekly_calories

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
    
    def distribute_weekly_calories(self,
                                   weekly_target: int,
                                   body_weight: Decimal,
                                   week_start_date: date,
                                   special_days: Optional[Dict[date, str]] = None,
                                   restaurant_estimates: Optional[Dict[date, int]] = None) -> WeeklyDistribution:
        """
        Distribute weekly calories across 7 days, reserving budget for special days
        (e.g. restaurants) and emitting safety warnings when daily totals dip below
        the per-pound minimum.
        """
        if special_days is None:
            special_days = {}
        if restaurant_estimates is None:
            restaurant_estimates = {}

        min_daily_calories = int(body_weight * self.minimum_calories_per_lb)
        daily_average = weekly_target // 7
        restaurant_buffer = 100  # default extra calories pre-allocated to restaurant days

        daily_targets: List[DailyCalorieTarget] = []
        safety_warnings: List[str] = []

        # Step 1: pre-allocate special days
        remaining_calories = weekly_target
        remaining_days = 7
        special_targets: Dict[date, int] = {}
        for i in range(7):
            current = week_start_date + timedelta(days=i)
            if current in special_days and special_days[current] == "restaurant":
                if current in restaurant_estimates:
                    target = restaurant_estimates[current]
                else:
                    target = daily_average + restaurant_buffer
                special_targets[current] = target
                remaining_calories -= target
                remaining_days -= 1

        # Step 2: distribute remaining across normal days
        avg_remaining = remaining_calories // remaining_days if remaining_days > 0 else 0
        for i in range(7):
            current = week_start_date + timedelta(days=i)
            if current in special_targets:
                final_target = special_targets[current]
                daily_targets.append(DailyCalorieTarget(
                    date=current,
                    base_target=daily_average,
                    banked_calories=0,
                    borrowed_calories=max(0, final_target - daily_average),
                    final_target=final_target,
                    is_special_event=True,
                    event_description=special_days.get(current),
                ))
                continue

            target = avg_remaining
            upcoming_special = self._get_upcoming_special_days(current, special_days, 3)
            if upcoming_special:
                reduction = min(restaurant_buffer * len(upcoming_special),
                                target - min_daily_calories)
                target -= reduction

            if target < min_daily_calories:
                safety_warnings.append(
                    f"{current.strftime('%A')}: Target {target} below minimum {min_daily_calories} calories"
                )
                target = min_daily_calories

            daily_targets.append(DailyCalorieTarget(
                date=current,
                base_target=daily_average,
                banked_calories=max(0, daily_average - target),
                borrowed_calories=max(0, target - daily_average),
                final_target=target,
                is_special_event=False,
            ))

        daily_targets.sort(key=lambda t: t.date)

        total_assigned = sum(t.final_target for t in daily_targets)
        total_banked = sum(t.banked_calories for t in daily_targets)
        total_borrowed = sum(t.borrowed_calories for t in daily_targets)

        return WeeklyDistribution(
            week_start_date=week_start_date,
            total_weekly_calories=total_assigned,
            daily_targets=daily_targets,
            total_banked=total_banked,
            total_borrowed=total_borrowed,
            is_balanced=(total_banked == total_borrowed),
            safety_warnings=safety_warnings,
        )

    def calculate_banking_impact(self,
                                 consumed_calories: int,
                                 target_calories: int,
                                 current_banked: int) -> Tuple[int, str]:
        """Apply a day's consumption to the running banked balance."""
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
        """Reduce other days to make room for an unplanned restaurant/event day."""
        min_daily_calories = int(body_weight * self.minimum_calories_per_lb)

        special_target = None
        other_targets = []
        for t in current_distribution.daily_targets:
            if t.date == special_date:
                special_target = t
            else:
                other_targets.append(t)

        if not special_target:
            return current_distribution

        excess_needed = estimated_calories - special_target.final_target
        if excess_needed <= 0 or not other_targets:
            return current_distribution

        days_to_reduce = len(other_targets)
        reduction_per_day = excess_needed // days_to_reduce
        remaining_reduction = excess_needed % days_to_reduce

        updated: List[DailyCalorieTarget] = []
        safety_warnings = list(current_distribution.safety_warnings)

        for i, t in enumerate(other_targets):
            reduction = reduction_per_day + (1 if i < remaining_reduction else 0)
            new_final = t.final_target - reduction
            if new_final < min_daily_calories:
                safety_warnings.append(
                    f"{t.date.strftime('%A')}: Cannot reduce below {min_daily_calories} calories"
                )
                new_final = min_daily_calories
            updated.append(DailyCalorieTarget(
                date=t.date,
                base_target=t.base_target,
                banked_calories=max(0, t.base_target - new_final),
                borrowed_calories=max(0, new_final - t.base_target),
                final_target=new_final,
                is_special_event=t.is_special_event,
                event_description=t.event_description,
            ))

        updated.append(DailyCalorieTarget(
            date=special_date,
            base_target=special_target.base_target,
            banked_calories=0,
            borrowed_calories=max(0, estimated_calories - special_target.base_target),
            final_target=estimated_calories,
            is_special_event=True,
            event_description="restaurant",
        ))
        updated.sort(key=lambda t: t.date)

        total_banked = sum(t.banked_calories for t in updated)
        total_borrowed = sum(t.borrowed_calories for t in updated)

        return WeeklyDistribution(
            week_start_date=current_distribution.week_start_date,
            total_weekly_calories=current_distribution.total_weekly_calories,
            daily_targets=updated,
            total_banked=total_banked,
            total_borrowed=total_borrowed,
            is_balanced=(total_banked == total_borrowed),
            safety_warnings=safety_warnings,
        )

    def _get_upcoming_special_days(self, current_date: date,
                                   special_days: Dict[date, str],
                                   look_ahead_days: int) -> List[date]:
        upcoming = []
        for i in range(1, look_ahead_days + 1):
            check_date = current_date + timedelta(days=i)
            if check_date in special_days:
                upcoming.append(check_date)
        return upcoming

    def validate_distribution_safety(self, distribution: WeeklyDistribution,
                                     body_weight: Decimal) -> List[str]:
        """Validate a built WeeklyDistribution against per-pound minimums and ceilings."""
        warnings: List[str] = []
        min_daily = int(body_weight * self.minimum_calories_per_lb)
        for t in distribution.daily_targets:
            if t.final_target < min_daily:
                warnings.append(
                    f"{t.date.strftime('%A')}: {t.final_target} calories below minimum {min_daily}"
                )
            if t.final_target > min_daily * 3:
                warnings.append(
                    f"{t.date.strftime('%A')}: {t.final_target} calories very high"
                )
        return warnings

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
