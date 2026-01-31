"""
Body Composition Service for calculating calorie targets and weight loss recommendations.
Based on body fat percentage and user goals.
"""
from decimal import Decimal
from typing import Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class BodyCompositionAssessment:
    """Results of body composition assessment."""
    body_fat_percentage: Decimal
    recommended_weight_loss_per_week: Decimal  # As percentage of body weight
    daily_calorie_target: int
    weekly_calorie_target: int
    assessment_category: str  # "lean", "average", "high_bf"

class BodyCompositionService:
    """Service for body composition assessment and calorie calculations."""
    
    def __init__(self):
        # Body fat percentage reference ranges (based on fitness industry standards)
        self.bf_categories = {
            "essential": (2, 5),      # Essential fat
            "athletes": (6, 13),      # Athletic range
            "fitness": (14, 17),      # Fitness range  
            "average": (18, 24),      # Average range
            "above_average": (25, 31), # Above average
            "obese": (32, 100)        # Obese range
        }
        
        # Weight loss recommendations based on body fat percentage
        self.weight_loss_recommendations = {
            "essential": Decimal("0.5"),    # 0.5% per week (very conservative)
            "athletes": Decimal("0.5"),     # 0.5% per week
            "fitness": Decimal("1.0"),      # 1.0% per week
            "average": Decimal("1.0"),      # 1.0% per week
            "above_average": Decimal("1.5"), # 1.5% per week
            "obese": Decimal("2.0")         # 2.0% per week (max safe rate)
        }
    
    def assess_body_composition(self, body_fat_percentage: Decimal, 
                              current_weight: Decimal,
                              activity_level: str = "moderate") -> BodyCompositionAssessment:
        """
        Assess body composition and provide recommendations.
        
        Args:
            body_fat_percentage: User's body fat percentage (from photo assessment)
            current_weight: Current weight in pounds
            activity_level: "sedentary", "light", "moderate", "active", "very_active"
            
        Returns:
            BodyCompositionAssessment with recommendations
        """
        # Determine body fat category
        bf_category = self._categorize_body_fat(body_fat_percentage)
        
        # Get weight loss recommendation
        recommended_loss_rate = self.weight_loss_recommendations[bf_category]
        
        # Calculate daily calorie needs
        bmr = self._calculate_bmr(current_weight, body_fat_percentage)
        tdee = self._calculate_tdee(bmr, activity_level)
        
        # Calculate calorie deficit for weight loss
        weekly_weight_loss = current_weight * (recommended_loss_rate / 100)
        weekly_calorie_deficit = int(weekly_weight_loss * 3500)  # 3500 cal per lb
        daily_calorie_deficit = weekly_calorie_deficit // 7
        
        # Calculate target calories
        daily_target = max(int(tdee - daily_calorie_deficit), int(current_weight * 10))  # Min 10 cal/lb
        weekly_target = daily_target * 7
        
        return BodyCompositionAssessment(
            body_fat_percentage=body_fat_percentage,
            recommended_weight_loss_per_week=recommended_loss_rate,
            daily_calorie_target=daily_target,
            weekly_calorie_target=weekly_target,
            assessment_category=bf_category
        )
    
    def _categorize_body_fat(self, bf_percentage: Decimal) -> str:
        """Categorize body fat percentage."""
        bf_float = float(bf_percentage)
        
        for category, (min_bf, max_bf) in self.bf_categories.items():
            if min_bf <= bf_float <= max_bf:
                return category
        
        return "average"  # Default fallback
    
    def _calculate_bmr(self, weight_lbs: Decimal, body_fat_percentage: Decimal) -> Decimal:
        """
        Calculate Basal Metabolic Rate using Katch-McArdle formula.
        More accurate for people who know their body fat percentage.
        """
        weight_kg = weight_lbs * Decimal("0.453592")  # Convert lbs to kg
        lean_mass_kg = weight_kg * (1 - body_fat_percentage / 100)
        
        # Katch-McArdle: BMR = 370 + (21.6 × lean body mass in kg)
        bmr = 370 + (Decimal("21.6") * lean_mass_kg)
        
        return bmr
    
    def _calculate_tdee(self, bmr: Decimal, activity_level: str) -> Decimal:
        """Calculate Total Daily Energy Expenditure."""
        activity_multipliers = {
            "sedentary": Decimal("1.2"),      # Little/no exercise
            "light": Decimal("1.375"),        # Light exercise 1-3 days/week
            "moderate": Decimal("1.55"),      # Moderate exercise 3-5 days/week
            "active": Decimal("1.725"),       # Heavy exercise 6-7 days/week
            "very_active": Decimal("1.9")     # Very heavy exercise, physical job
        }
        
        multiplier = activity_multipliers.get(activity_level, Decimal("1.55"))
        return bmr * multiplier
    
    def get_photo_reference_ranges(self) -> Dict[str, Tuple[int, int]]:
        """
        Get body fat percentage ranges for photo reference slider.
        Returns ranges that users can select from photos.
        """
        return {
            "very_lean": (8, 12),      # Very defined abs, vascular
            "lean": (13, 17),          # Visible abs, some definition
            "average": (18, 24),       # Some muscle definition
            "soft": (25, 31),          # Minimal definition, soft appearance
            "high": (32, 40)           # No visible definition
        }
    
    def validate_calorie_target(self, target_calories: int, body_weight: Decimal) -> Tuple[bool, str]:
        """
        Validate that calorie target meets minimum safety requirements.
        
        Returns:
            (is_valid, message)
        """
        min_calories = int(body_weight * 10)  # 10 calories per pound minimum
        
        if target_calories < min_calories:
            return False, f"Target too low. Minimum {min_calories} calories for {body_weight} lbs body weight."
        
        if target_calories > int(body_weight * 20):  # Reasonable upper limit
            return False, f"Target very high. Consider consulting a nutritionist."
        
        return True, "Target is within safe range."
