"""
Weight Tracking Service - TDEE Estimation and Progress Monitoring
Clean Architecture - Business Logic Layer
"""
from decimal import Decimal
from typing import List, Optional, Tuple
from datetime import date, timedelta
from dataclasses import dataclass

@dataclass
class WeightLog:
    """Weight log entry with progress tracking."""
    user_id: str
    date: date
    weight: Decimal
    notes: Optional[str] = None

@dataclass
class WeightProgress:
    """Weight progress analysis."""
    current_weight: Decimal
    previous_weight: Optional[Decimal]
    weekly_change: Optional[Decimal]  # Positive = gain, Negative = loss
    weekly_change_percentage: Optional[Decimal]
    trend_direction: str  # "losing", "gaining", "maintaining"

@dataclass
class TDEEEstimate:
    """TDEE estimation based on weight and calorie data."""
    estimated_tdee: int
    confidence_level: str  # "high", "medium", "low"
    data_points_used: int
    recommended_deficit: int  # For weight loss goals
    recommended_daily_calories: int

class WeightTrackingService:
    """Service for weight tracking, progress analysis, and TDEE estimation."""
    
    def calculate_weekly_average_change(self, weight_logs: List[WeightLog]) -> Optional[Decimal]:
        """
        Calculate weekly average weight change from recent logs.
        
        Args:
            weight_logs: List of weight logs (should be sorted by date desc)
            
        Returns:
            Weekly average change in weight (lbs/week)
        """
        if len(weight_logs) < 2:
            return None
        
        # Use last 4 weeks of data for stability
        recent_logs = weight_logs[:28]  # Up to 28 days
        if len(recent_logs) < 7:
            return None
        
        # Calculate weekly averages
        weekly_averages = []
        current_date = recent_logs[0].date
        
        for week in range(4):  # Look at 4 weeks
            week_start = current_date - timedelta(days=week * 7)
            week_end = week_start - timedelta(days=6)
            
            week_weights = [
                log.weight for log in recent_logs 
                if week_end <= log.date <= week_start
            ]
            
            if week_weights:
                weekly_averages.append(sum(week_weights) / len(week_weights))
        
        if len(weekly_averages) < 2:
            return None
        
        # Calculate average weekly change
        total_change = weekly_averages[0] - weekly_averages[-1]
        weeks_span = len(weekly_averages) - 1
        
        return total_change / weeks_span
    
    def analyze_weight_progress(self, weight_logs: List[WeightLog]) -> WeightProgress:
        """
        Analyze weight progress and trends.
        
        Args:
            weight_logs: List of weight logs (sorted by date desc)
            
        Returns:
            Weight progress analysis
        """
        if not weight_logs:
            return WeightProgress(
                current_weight=Decimal('0'),
                previous_weight=None,
                weekly_change=None,
                weekly_change_percentage=None,
                trend_direction="unknown"
            )
        
        current_weight = weight_logs[0].weight
        previous_weight = weight_logs[1].weight if len(weight_logs) > 1 else None
        
        weekly_change = self.calculate_weekly_average_change(weight_logs)
        weekly_change_percentage = None
        
        if weekly_change and current_weight > 0:
            weekly_change_percentage = (weekly_change / current_weight) * 100
        
        # Determine trend direction
        trend_direction = "maintaining"
        if weekly_change:
            if weekly_change < -Decimal('0.5'):
                trend_direction = "losing"
            elif weekly_change > Decimal('0.5'):
                trend_direction = "gaining"
        
        return WeightProgress(
            current_weight=current_weight,
            previous_weight=previous_weight,
            weekly_change=weekly_change,
            weekly_change_percentage=weekly_change_percentage,
            trend_direction=trend_direction
        )
    
    def estimate_tdee(self, weight_logs: List[WeightLog], calorie_logs: List, 
                     user_weight: Decimal) -> TDEEEstimate:
        """
        Estimate TDEE based on weight change and calorie intake.
        
        Args:
            weight_logs: Recent weight logs
            calorie_logs: Recent calorie consumption logs
            user_weight: Current user weight
            
        Returns:
            TDEE estimation with confidence level
        """
        # Need at least 2 weeks of data for reasonable estimate
        if len(weight_logs) < 14 or len(calorie_logs) < 14:
            return self._default_tdee_estimate(user_weight)
        
        # Calculate average daily calories over period
        total_calories = sum(log.consumed_calories for log in calorie_logs)
        avg_daily_calories = total_calories / len(calorie_logs)
        
        # Calculate weight change over period.
        # Logs are sorted newest-first, so weight_lost = oldest - newest.
        # Positive weight_lost => deficit => TDEE > consumed.
        weight_lost = weight_logs[-1].weight - weight_logs[0].weight
        days_span = (weight_logs[0].date - weight_logs[-1].date).days
        
        if days_span == 0:
            return self._default_tdee_estimate(user_weight)
        
        # 1 lb = ~3500 calories
        calories_per_pound = 3500
        
        # Calculate implied TDEE
        # If losing weight: TDEE = avg_calories + (weight_lost * 3500 / days)
        # If gaining weight: TDEE = avg_calories - (weight_gained * 3500 / days)
        daily_calorie_deficit = float(weight_lost * calories_per_pound) / days_span
        estimated_tdee = int(avg_daily_calories + daily_calorie_deficit)
        
        # Determine confidence level
        confidence_level = "low"
        if len(weight_logs) >= 28 and len(calorie_logs) >= 28:
            confidence_level = "high"
        elif len(weight_logs) >= 21 and len(calorie_logs) >= 21:
            confidence_level = "medium"
        
        # Calculate recommended deficit for weight loss (1-2 lbs/week)
        recommended_deficit = min(int(user_weight * Decimal('0.01') * 3500 / 7), 1000)  # Max 1000 cal deficit
        recommended_daily_calories = max(estimated_tdee - recommended_deficit, 
                                       int(user_weight * 10))  # Min 10 cal/lb
        
        return TDEEEstimate(
            estimated_tdee=estimated_tdee,
            confidence_level=confidence_level,
            data_points_used=len(calorie_logs),
            recommended_deficit=recommended_deficit,
            recommended_daily_calories=recommended_daily_calories
        )
    
    def _default_tdee_estimate(self, user_weight: Decimal) -> TDEEEstimate:
        """
        Provide default TDEE estimate when insufficient data.
        
        Args:
            user_weight: User's current weight
            
        Returns:
            Conservative TDEE estimate
        """
        # Conservative estimate: 12-15 calories per pound for sedentary to moderate activity
        estimated_tdee = int(user_weight * 13)
        recommended_deficit = min(int(user_weight * Decimal('0.01') * 3500 / 7), 750)
        recommended_daily_calories = max(estimated_tdee - recommended_deficit, 
                                       int(user_weight * 10))
        
        return TDEEEstimate(
            estimated_tdee=estimated_tdee,
            confidence_level="low",
            data_points_used=0,
            recommended_deficit=recommended_deficit,
            recommended_daily_calories=recommended_daily_calories
        )
    
    def calculate_target_weight_loss_rate(self, current_bf_percentage: Optional[Decimal]) -> Decimal:
        """
        Calculate recommended weekly weight loss rate based on body fat percentage.
        
        Args:
            current_bf_percentage: Current body fat percentage
            
        Returns:
            Recommended weekly weight loss rate as percentage of body weight
        """
        if not current_bf_percentage:
            return Decimal('1.0')  # Default 1% per week
        
        # More aggressive rates for higher body fat
        if current_bf_percentage >= 25:  # 25%+ BF
            return Decimal('2.0')  # Up to 2% per week
        elif current_bf_percentage >= 20:  # 20-25% BF
            return Decimal('1.5')  # Up to 1.5% per week
        elif current_bf_percentage >= 15:  # 15-20% BF
            return Decimal('1.0')  # Up to 1% per week
        else:  # <15% BF
            return Decimal('0.5')  # Conservative 0.5% per week
