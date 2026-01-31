"""
Enhanced Grocery List Generator with Calorie Banking Integration.
Generates shopping lists based on weekly calorie distribution and macro targets.
"""
from typing import List, Dict, Optional, Tuple
from datetime import date, timedelta
from decimal import Decimal
from dataclasses import dataclass

# Import our services
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.services.calorie_banking_service import CalorieBankingService, WeeklyDistribution
from core.services.macro_tracking_service import MacroTrackingService, MacroTargets
from core.services.recipe_scaler import RecipeScaler
from core.services.ingredient_aggregator import IngredientAggregator

@dataclass
class WeeklyMealPlan:
    """Complete weekly meal plan with calorie and macro targets."""
    week_start: date
    daily_plans: Dict[date, Dict]  # {date: {"recipes": [...], "targets": MacroTargets}}
    grocery_list: Dict[str, Decimal]  # {ingredient: total_amount}
    weekly_totals: Dict[str, int]  # {"calories": X, "protein": Y, "carbs": Z, "fats": W}

class EnhancedGroceryListGenerator:
    """Enhanced grocery list generator with flexible dieting integration."""
    
    def __init__(self):
        self.calorie_service = CalorieBankingService()
        self.macro_service = MacroTrackingService()
        self.recipe_scaler = RecipeScaler()
        self.ingredient_aggregator = IngredientAggregator()
    
    def generate_weekly_meal_plan(self,
                                user_id: int,
                                weekly_calorie_target: int,
                                body_weight: Decimal,
                                week_start_date: date,
                                user_selected_recipes: Dict[date, List[Dict]],
                                special_days: Dict[date, str] = None,
                                activity_level: str = "moderate") -> WeeklyMealPlan:
        """
        Generate complete weekly meal plan with grocery list from user-selected recipes.
        
        Args:
            user_id: User identifier
            weekly_calorie_target: Total calories for the week
            body_weight: User's body weight in pounds
            week_start_date: Monday of the week to plan
            user_selected_recipes: Dict of {date: [recipe_dicts]} - user's recipe choices
            special_days: Optional special days (restaurant, etc.)
            activity_level: User's activity level for macro calculations
            
        Returns:
            WeeklyMealPlan with daily targets and grocery list
        """
        # Step 1: Get weekly calorie distribution
        calorie_distribution = self.calorie_service.distribute_weekly_calories(
            weekly_target=weekly_calorie_target,
            body_weight=body_weight,
            week_start_date=week_start_date,
            special_days=special_days or {}
        )
        
        # Step 2: Calculate daily macro targets for each day
        daily_plans = {}
        all_ingredients = {}
        weekly_totals = {"calories": 0, "protein": 0, "carbs": 0, "fats": 0}
        
        for daily_target in calorie_distribution.daily_targets:
            current_date = daily_target.date
            
            # Skip special days (user will eat out)
            if daily_target.is_special_day:
                daily_plans[current_date] = {
                    "recipes": [],
                    "targets": None,
                    "note": f"Special day: {daily_target.special_day_type}"
                }
                continue
            
            # Calculate macro targets for this day
            macro_targets = self.macro_service.calculate_macro_targets(
                daily_calories=daily_target.target_calories,
                body_weight=body_weight,
                activity_level=activity_level
            )
            
            # Get user's selected recipes for this day
            selected_recipes = user_selected_recipes.get(current_date, [])
            
            # Aggregate ingredients for this day
            day_ingredients = self._get_day_ingredients(selected_recipes)
            
            # Add to weekly totals
            for ingredient, amount in day_ingredients.items():
                if ingredient in all_ingredients:
                    all_ingredients[ingredient] += amount
                else:
                    all_ingredients[ingredient] = amount
            
            # Calculate actual totals for this day
            day_totals = self._calculate_day_totals(selected_recipes)
            weekly_totals["calories"] += day_totals["calories"]
            weekly_totals["protein"] += day_totals["protein"]
            weekly_totals["carbs"] += day_totals["carbs"]
            weekly_totals["fats"] += day_totals["fats"]
            
            daily_plans[current_date] = {
                "recipes": selected_recipes,
                "targets": macro_targets,
                "actual": day_totals,
                "analysis": self._analyze_day_targets(day_totals, macro_targets, "free")  # Default to free tier
            }
        
        return WeeklyMealPlan(
            week_start=week_start_date,
            daily_plans=daily_plans,
            grocery_list=all_ingredients,
            weekly_totals=weekly_totals
        )
    
    def analyze_user_recipe_choices(self, 
                                  user_selected_recipes: Dict[date, List[Dict]],
                                  calorie_distribution: 'WeeklyDistribution',
                                  body_weight: Decimal,
                                  activity_level: str = "moderate",
                                  user_tier: str = "free") -> Dict[date, Dict]:
        """
        Analyze how well user's recipe choices match their calorie and macro targets.
        
        Args:
            user_selected_recipes: User's recipe choices by date
            calorie_distribution: Weekly calorie distribution with daily targets
            body_weight: User's body weight for macro calculations
            activity_level: Activity level for macro targets
            
        Returns:
            Dict of {date: analysis_results} with suggestions and gaps
        """
        analysis_results = {}
        
        for daily_target in calorie_distribution.daily_targets:
            current_date = daily_target.date
            
            if daily_target.is_special_day:
                continue
            
            # Calculate targets for this day
            macro_targets = self.macro_service.calculate_macro_targets(
                daily_calories=daily_target.target_calories,
                body_weight=body_weight,
                activity_level=activity_level
            )
            
            # Get user's recipes for this day
            selected_recipes = user_selected_recipes.get(current_date, [])
            
            # Calculate actual totals
            day_totals = self._calculate_day_totals(selected_recipes)
            
            # Analyze gaps and provide suggestions
            analysis = self._analyze_day_targets(day_totals, macro_targets, user_tier)
            
            analysis_results[current_date] = {
                "targets": macro_targets,
                "actual": day_totals,
                "analysis": analysis,
                "recipes": selected_recipes
            }
        
        return analysis_results
    
    def adjust_plan_for_special_day(self,
                                  current_plan: WeeklyMealPlan,
                                  special_date: date,
                                  estimated_calories: int,
                                  body_weight: Decimal) -> WeeklyMealPlan:
        """
        Adjust existing meal plan when user adds a special day.
        
        Args:
            current_plan: Current weekly meal plan
            special_date: Date of the special day
            estimated_calories: Estimated calories for special day
            body_weight: User's body weight for safety calculations
            
        Returns:
            Updated WeeklyMealPlan with redistributed calories
        """
        # Get current calorie distribution
        current_distribution = self._extract_calorie_distribution(current_plan)
        
        # Redistribute calories
        new_distribution = self.calorie_service.redistribute_for_special_day(
            current_distribution=current_distribution,
            special_date=special_date,
            estimated_calories=estimated_calories,
            body_weight=body_weight
        )
        
        # Regenerate meal plan with new distribution
        # (This would typically call generate_weekly_meal_plan with updated targets)
        # For now, return the current plan with a note
        updated_plan = current_plan
        updated_plan.daily_plans[special_date] = {
            "recipes": [],
            "targets": None,
            "note": f"Special day: restaurant ({estimated_calories} calories)"
        }
        
        return updated_plan
    
    def generate_shopping_list_with_inventory(self,
                                           meal_plan: WeeklyMealPlan,
                                           current_inventory: Dict[str, Decimal]) -> Dict[str, Decimal]:
        """
        Generate shopping list accounting for current inventory.
        
        Args:
            meal_plan: Weekly meal plan with ingredient requirements
            current_inventory: Current inventory {ingredient: amount}
            
        Returns:
            Shopping list {ingredient: amount_to_buy}
        """
        shopping_list = {}
        
        for ingredient, needed_amount in meal_plan.grocery_list.items():
            current_amount = current_inventory.get(ingredient, Decimal("0"))
            
            if needed_amount > current_amount:
                to_buy = needed_amount - current_amount
                shopping_list[ingredient] = to_buy
        
        return shopping_list
    
    def _analyze_day_targets(self, actual_totals: Dict[str, int], 
                           macro_targets: MacroTargets,
                           user_tier: str = "free") -> Dict[str, any]:
        """Analyze how well actual totals match targets with tier-based features."""
        calorie_diff = actual_totals["calories"] - macro_targets.calories
        protein_diff = actual_totals["protein"] - macro_targets.protein_g
        carbs_diff = actual_totals["carbs"] - macro_targets.carbs_g
        fats_diff = actual_totals["fats"] - macro_targets.fats_g
        
        # Basic analysis (available to all users)
        basic_gaps = []
        if calorie_diff < -200:
            basic_gaps.append(f"Need {abs(calorie_diff)} more calories")
        elif calorie_diff > 200:
            basic_gaps.append(f"Over by {calorie_diff} calories")
        
        if protein_diff < -20:
            basic_gaps.append(f"Need {abs(protein_diff)}g more protein")
        if carbs_diff < -30:
            basic_gaps.append(f"Need {abs(carbs_diff)}g more carbs")
        if fats_diff < -15:
            basic_gaps.append(f"Need {abs(fats_diff)}g more fats")
        
        analysis = {
            "calorie_diff": calorie_diff,
            "protein_diff": protein_diff,
            "carbs_diff": carbs_diff,
            "fats_diff": fats_diff,
            "basic_gaps": basic_gaps,
            "status": "good" if len(basic_gaps) == 0 else "needs_adjustment"
        }
        
        # Premium features (only for premium users)
        if user_tier == "premium":
            analysis["premium_suggestions"] = self._generate_premium_suggestions(
                calorie_diff, protein_diff, carbs_diff, fats_diff
            )
            analysis["smart_recipes"] = self._suggest_smart_recipes(
                calorie_diff, protein_diff, carbs_diff, fats_diff
            )
            analysis["meal_timing"] = self._suggest_meal_timing(actual_totals, macro_targets)
        else:
            # Free users see upgrade prompt
            analysis["upgrade_prompt"] = "Upgrade to Premium for personalized recipe suggestions and meal timing advice"
        
        return analysis
    
    def _generate_premium_suggestions(self, calorie_diff: int, protein_diff: int, 
                                    carbs_diff: int, fats_diff: int) -> List[str]:
        """Generate premium personalized suggestions (premium feature)."""
        suggestions = []
        
        # Smart protein suggestions
        if protein_diff < -20:
            if protein_diff < -50:
                suggestions.append("High protein gap: Try protein powder (30g) + Greek yogurt (20g)")
            else:
                suggestions.append("Moderate protein gap: Try chicken breast (25g) or cottage cheese (15g)")
        
        # Smart carb suggestions
        if carbs_diff < -30:
            if calorie_diff < -500:  # Need lots of calories too
                suggestions.append("High energy gap: Try oatmeal with banana (60g carbs, 300 cal)")
            else:
                suggestions.append("Carb gap: Try rice (45g) or sweet potato (30g)")
        
        # Smart fat suggestions
        if fats_diff < -15:
            suggestions.append("Healthy fats: Try avocado (15g), nuts (20g), or olive oil (10g)")
        
        # Calorie-specific suggestions
        if calorie_diff < -300:
            suggestions.append("Quick calories: Protein smoothie (400 cal) or peanut butter sandwich (350 cal)")
        
        return suggestions
    
    def _suggest_smart_recipes(self, calorie_diff: int, protein_diff: int,
                             carbs_diff: int, fats_diff: int) -> List[Dict]:
        """Suggest specific recipes to fill macro gaps (premium feature)."""
        recipe_suggestions = []
        
        # High protein recipes
        if protein_diff < -30:
            recipe_suggestions.append({
                "name": "Protein Power Bowl",
                "calories": 350,
                "protein": 40,
                "carbs": 20,
                "fats": 12,
                "reason": "Fills protein gap efficiently"
            })
        
        # High carb recipes
        if carbs_diff < -40:
            recipe_suggestions.append({
                "name": "Energy Rice Bowl",
                "calories": 400,
                "protein": 15,
                "carbs": 65,
                "fats": 8,
                "reason": "Provides sustained energy"
            })
        
        # Balanced recipes for general gaps
        if calorie_diff < -400:
            recipe_suggestions.append({
                "name": "Balanced Meal Replacement",
                "calories": 450,
                "protein": 25,
                "carbs": 35,
                "fats": 20,
                "reason": "Balanced macro profile"
            })
        
        return recipe_suggestions
    
    def _suggest_meal_timing(self, actual_totals: Dict[str, int], 
                           macro_targets: MacroTargets) -> Dict[str, str]:
        """Suggest optimal meal timing (premium feature)."""
        timing_advice = {}
        
        protein_gap = macro_targets.protein_g - actual_totals["protein"]
        carbs_gap = macro_targets.carbs_g - actual_totals["carbs"]
        
        if protein_gap > 30:
            timing_advice["protein"] = "Spread remaining protein across 2-3 meals for better absorption"
        
        if carbs_gap > 50:
            timing_advice["carbs"] = "Consider carbs around workout times for optimal energy"
        
        if actual_totals["calories"] < macro_targets.calories * 0.5:
            timing_advice["general"] = "Front-load calories earlier in the day for better energy levels"
        
        return timing_advice
    
    def _get_day_ingredients(self, recipes: List[Dict]) -> Dict[str, Decimal]:
        """Extract and aggregate ingredients from daily recipes."""
        all_ingredients = {}
        
        for recipe in recipes:
            # Extract ingredients from recipe dict format
            ingredients = recipe.get("ingredients", [])
            
            for ingredient in ingredients:
                ingredient_name = ingredient["name"]
                amount = Decimal(str(ingredient["amount"]))
                
                if ingredient_name in all_ingredients:
                    all_ingredients[ingredient_name] += amount
                else:
                    all_ingredients[ingredient_name] = amount
        
        return all_ingredients
    
    def _calculate_day_totals(self, recipes: List[Dict]) -> Dict[str, int]:
        """Calculate total calories and macros for a day's recipes."""
        totals = {"calories": 0, "protein": 0, "carbs": 0, "fats": 0}
        
        for recipe in recipes:
            servings = recipe.get("servings", 1)
            totals["calories"] += recipe.get("calories_per_serving", 0) * servings
            totals["protein"] += recipe.get("protein_per_serving", 0) * servings
            totals["carbs"] += recipe.get("carbs_per_serving", 0) * servings
            totals["fats"] += recipe.get("fats_per_serving", 0) * servings
        
        return totals
    
    def _extract_calorie_distribution(self, meal_plan: WeeklyMealPlan) -> 'WeeklyDistribution':
        """Extract calorie distribution from existing meal plan."""
        from core.services.calorie_banking_service import DailyCalorieTarget, WeeklyDistribution
        
        daily_targets = []
        total_calories = 0
        
        for plan_date, plan_data in meal_plan.daily_plans.items():
            if plan_data["targets"]:
                calories = plan_data["targets"].calories
            else:
                calories = 0  # Special day
            
            daily_targets.append(DailyCalorieTarget(
                date=plan_date,
                target_calories=calories,
                is_special_day=plan_data.get("note") is not None
            ))
            total_calories += calories
        
        return WeeklyDistribution(
            weekly_target=total_calories,
            daily_targets=daily_targets,
            total_banked=0,
            safety_warnings=[]
        )
