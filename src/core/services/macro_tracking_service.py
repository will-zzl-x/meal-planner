"""
Macro Tracking Service for protein, carbs, and fats management.
Integrates with calorie banking for comprehensive nutrition tracking.
"""
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import date

@dataclass
class MacroTargets:
    """Daily macro targets in grams."""
    protein_g: int
    carbs_g: int
    fats_g: int
    calories: int
    
    @property
    def protein_calories(self) -> int:
        return self.protein_g * 4
    
    @property
    def carbs_calories(self) -> int:
        return self.carbs_g * 4
    
    @property
    def fats_calories(self) -> int:
        return self.fats_g * 9

@dataclass
class MacroIntake:
    """Actual macro intake for a day."""
    protein_g: Decimal
    carbs_g: Decimal
    fats_g: Decimal
    
    @property
    def total_calories(self) -> int:
        return int((self.protein_g * 4) + (self.carbs_g * 4) + (self.fats_g * 9))

@dataclass
class MacroProgress:
    """Progress tracking for macros."""
    targets: MacroTargets
    current: MacroIntake
    remaining_protein: int
    remaining_carbs: int
    remaining_fats: int
    remaining_calories: int

class MacroTrackingService:
    """Service for macro nutrient tracking and target calculations."""
    
    def __init__(self):
        # Standard macro ratios (can be customized per user)
        self.default_protein_ratio = 0.30  # 30% of calories from protein
        self.default_carbs_ratio = 0.40    # 40% of calories from carbs
        self.default_fats_ratio = 0.30     # 30% of calories from fats
        
        # Minimum protein per pound body weight
        self.min_protein_per_lb = Decimal("0.8")  # 0.8g per lb minimum
        self.optimal_protein_per_lb = Decimal("1.0")  # 1g per lb optimal
    
    def calculate_macro_targets(self, 
                              daily_calories: int,
                              body_weight: Decimal,
                              activity_level: str = "moderate",
                              custom_ratios: Optional[Dict[str, float]] = None) -> MacroTargets:
        """
        Calculate daily macro targets based on calories and body composition.
        
        Args:
            daily_calories: Target calories for the day
            body_weight: Body weight in pounds
            activity_level: "sedentary", "moderate", "active", "very_active"
            custom_ratios: Optional custom macro ratios {"protein": 0.3, "carbs": 0.4, "fats": 0.3}
            
        Returns:
            MacroTargets with protein, carbs, fats in grams
        """
        # Use custom ratios or defaults
        if custom_ratios:
            protein_ratio = custom_ratios.get("protein", self.default_protein_ratio)
            carbs_ratio = custom_ratios.get("carbs", self.default_carbs_ratio)
            fats_ratio = custom_ratios.get("fats", self.default_fats_ratio)
        else:
            protein_ratio, carbs_ratio, fats_ratio = self._get_activity_ratios(activity_level)
        
        # Calculate protein based on body weight (prioritize this)
        min_protein = int(body_weight * self.min_protein_per_lb)
        ratio_protein = int((daily_calories * protein_ratio) / 4)
        protein_g = max(min_protein, ratio_protein)
        
        # Calculate remaining calories for carbs and fats
        remaining_calories = daily_calories - (protein_g * 4)
        
        # Distribute remaining calories between carbs and fats
        carbs_calories = int(remaining_calories * (carbs_ratio / (carbs_ratio + fats_ratio)))
        fats_calories = remaining_calories - carbs_calories
        
        carbs_g = carbs_calories // 4
        fats_g = fats_calories // 9
        
        return MacroTargets(
            protein_g=protein_g,
            carbs_g=carbs_g,
            fats_g=fats_g,
            calories=daily_calories
        )
    
    def calculate_recipe_macros(self, recipe_data: Dict) -> MacroIntake:
        """
        Calculate macros from recipe ingredient data.
        
        Args:
            recipe_data: Dict with ingredients and their macro values
            Format: {
                "ingredients": [
                    {"name": "chicken breast", "amount": 200, "protein_per_100g": 31, "carbs_per_100g": 0, "fats_per_100g": 3.6},
                    {"name": "rice", "amount": 150, "protein_per_100g": 2.7, "carbs_per_100g": 28, "fats_per_100g": 0.3}
                ]
            }
            
        Returns:
            MacroIntake with total macros for the recipe
        """
        total_protein = Decimal("0")
        total_carbs = Decimal("0")
        total_fats = Decimal("0")
        
        for ingredient in recipe_data.get("ingredients", []):
            amount_g = Decimal(str(ingredient["amount"]))
            
            # Calculate macros based on per-100g values
            protein = (amount_g / 100) * Decimal(str(ingredient.get("protein_per_100g", 0)))
            carbs = (amount_g / 100) * Decimal(str(ingredient.get("carbs_per_100g", 0)))
            fats = (amount_g / 100) * Decimal(str(ingredient.get("fats_per_100g", 0)))
            
            total_protein += protein
            total_carbs += carbs
            total_fats += fats
        
        return MacroIntake(
            protein_g=total_protein,
            carbs_g=total_carbs,
            fats_g=total_fats
        )
    
    def track_daily_progress(self, 
                           targets: MacroTargets,
                           consumed_recipes: List[Dict]) -> MacroProgress:
        """
        Track macro progress for the day.
        
        Args:
            targets: Daily macro targets
            consumed_recipes: List of recipe data consumed today
            
        Returns:
            MacroProgress with current status and remaining targets
        """
        # Calculate total consumed macros
        total_consumed = MacroIntake(
            protein_g=Decimal("0"),
            carbs_g=Decimal("0"),
            fats_g=Decimal("0")
        )
        
        for recipe in consumed_recipes:
            recipe_macros = self.calculate_recipe_macros(recipe)
            total_consumed.protein_g += recipe_macros.protein_g
            total_consumed.carbs_g += recipe_macros.carbs_g
            total_consumed.fats_g += recipe_macros.fats_g
        
        # Calculate remaining targets
        remaining_protein = max(0, targets.protein_g - int(total_consumed.protein_g))
        remaining_carbs = max(0, targets.carbs_g - int(total_consumed.carbs_g))
        remaining_fats = max(0, targets.fats_g - int(total_consumed.fats_g))
        remaining_calories = max(0, targets.calories - total_consumed.total_calories)
        
        return MacroProgress(
            targets=targets,
            current=total_consumed,
            remaining_protein=remaining_protein,
            remaining_carbs=remaining_carbs,
            remaining_fats=remaining_fats,
            remaining_calories=remaining_calories
        )
    
    def suggest_macro_adjustments(self, progress: MacroProgress) -> List[str]:
        """
        Suggest adjustments to hit macro targets.
        
        Returns:
            List of actionable suggestions
        """
        suggestions = []
        
        # Protein suggestions
        if progress.remaining_protein > 20:
            suggestions.append(f"Add {progress.remaining_protein}g protein (lean meat, protein powder, Greek yogurt)")
        elif progress.remaining_protein > 0:
            suggestions.append(f"Add {progress.remaining_protein}g protein (eggs, cottage cheese)")
        
        # Carb suggestions
        if progress.remaining_carbs > 30:
            suggestions.append(f"Add {progress.remaining_carbs}g carbs (rice, oats, fruit)")
        elif progress.remaining_carbs > 0:
            suggestions.append(f"Add {progress.remaining_carbs}g carbs (vegetables, berries)")
        
        # Fat suggestions
        if progress.remaining_fats > 15:
            suggestions.append(f"Add {progress.remaining_fats}g fats (nuts, olive oil, avocado)")
        elif progress.remaining_fats > 0:
            suggestions.append(f"Add {progress.remaining_fats}g fats (seeds, nut butter)")
        
        # Overall calorie check
        if progress.remaining_calories > 200:
            suggestions.append(f"Need {progress.remaining_calories} more calories - consider a balanced snack")
        elif progress.remaining_calories < -200:
            suggestions.append("Over calorie target - consider lighter options for remaining meals")
        
        return suggestions
    
    def calculate_weekly_macro_average(self, daily_targets: List[MacroTargets]) -> MacroTargets:
        """Calculate average weekly macro targets."""
        if not daily_targets:
            return MacroTargets(0, 0, 0, 0)
        
        total_protein = sum(t.protein_g for t in daily_targets)
        total_carbs = sum(t.carbs_g for t in daily_targets)
        total_fats = sum(t.fats_g for t in daily_targets)
        total_calories = sum(t.calories for t in daily_targets)
        
        days = len(daily_targets)
        
        return MacroTargets(
            protein_g=total_protein // days,
            carbs_g=total_carbs // days,
            fats_g=total_fats // days,
            calories=total_calories // days
        )
    
    def _get_activity_ratios(self, activity_level: str) -> Tuple[float, float, float]:
        """Get macro ratios based on activity level."""
        ratios = {
            "sedentary": (0.25, 0.45, 0.30),     # Lower protein, higher carbs
            "moderate": (0.30, 0.40, 0.30),      # Balanced
            "active": (0.35, 0.40, 0.25),        # Higher protein, lower fats
            "very_active": (0.40, 0.45, 0.15)    # High protein, high carbs, low fats
        }
        
        return ratios.get(activity_level, ratios["moderate"])
