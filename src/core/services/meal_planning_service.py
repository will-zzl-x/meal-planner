"""
Enhanced Meal Planning Service - User-driven meal selection with food database integration
Clean Architecture - Business Logic Layer
"""
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from datetime import date, timedelta
from dataclasses import dataclass

# Import from core layer
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.domain.models import Recipe, InventoryItem, GroceryListItem
from core.services import IngredientAggregator, RecipeScaler, UnitConverter, InventoryService
from core.services.flexible_dieting import CalorieBankingService, WeightTrackingService

@dataclass
class FoodItem:
    """Individual food item from database (not a recipe)."""
    name: str
    calories_per_100g: int
    protein_g: Decimal
    carbs_g: Decimal
    fat_g: Decimal
    serving_size: str  # "100g", "1 cup", "1 piece", etc.
    category: str  # "food" or "restaurant"

@dataclass
class MealPlanEntry:
    """Single meal plan entry - can be recipe or individual food item."""
    date: date
    meal_type: str  # "breakfast", "lunch", "dinner", "snack"
    item_type: str  # "recipe" or "food_item"
    recipe: Optional[Recipe] = None
    food_item: Optional[FoodItem] = None
    servings: Decimal = Decimal('1')
    quantity: Decimal = Decimal('1')  # For food items
    calories: int = 0
    protein_grams: Decimal = Decimal('0')
    carb_grams: Decimal = Decimal('0')
    fat_grams: Decimal = Decimal('0')

@dataclass
class DailyMealPlan:
    """Complete meal plan for a single day."""
    date: date
    user_id: str
    target_calories: int
    meals: List[MealPlanEntry]
    total_calories: int
    total_protein: Decimal
    total_carbs: Decimal
    total_fats: Decimal
    calories_remaining: int

@dataclass
class WeeklyMealPlan:
    """Complete meal plan for a week with grocery list."""
    household_id: str
    week_start_date: date
    daily_plans: Dict[str, List[DailyMealPlan]]  # user_id -> daily plans
    grocery_list: List[GroceryListItem]
    total_weekly_calories: Dict[str, int]  # user_id -> total calories

class MealPlanningService:
    """Service for user-driven meal planning with food database integration."""
    
    def __init__(self):
        """Initialize meal planning service with required components."""
        self._aggregator = IngredientAggregator()
        self._scaler = RecipeScaler()
        self._converter = UnitConverter()
        self._inventory_service = InventoryService()
        self._calorie_banking = CalorieBankingService()
        self._food_database = self._create_sample_food_database()
    
    def _create_sample_food_database(self) -> List[FoodItem]:
        """Create sample food database (would connect to real API in production)."""
        return [
            FoodItem("Almonds", 160, Decimal('6'), Decimal('6'), Decimal('14'), "oz", "snack"),
            FoodItem("Mandarin Orange", 35, Decimal('0.6'), Decimal('9'), Decimal('0.2'), "piece", "fruit"),
            FoodItem("Greek Yogurt", 100, Decimal('17'), Decimal('6'), Decimal('0'), "cup", "dairy"),
            FoodItem("Banana", 105, Decimal('1.3'), Decimal('27'), Decimal('0.4'), "piece", "fruit"),
            FoodItem("Protein Powder", 120, Decimal('25'), Decimal('3'), Decimal('1'), "scoop", "supplement"),
            FoodItem("Multivitamin", 0, Decimal('0'), Decimal('0'), Decimal('0'), "tablet", "supplement"),
            FoodItem("Big Mac", 550, Decimal('25'), Decimal('45'), Decimal('31'), "piece", "restaurant"),
            FoodItem("Chipotle Burrito Bowl", 650, Decimal('32'), Decimal('65'), Decimal('25'), "bowl", "restaurant"),
        ]
    
    def search_food_database(self, query: str, category: Optional[str] = None) -> List[FoodItem]:
        """
        Search food database for items matching query.
        
        Args:
            query: Search term
            category: Optional category filter
            
        Returns:
            List of matching food items
        """
        results = []
        query_lower = query.lower()
        
        for food_item in self._food_database:
            # Check if query matches name
            if query_lower in food_item.name.lower():
                # Check category filter if provided
                if category is None or food_item.category == category:
                    results.append(food_item)
        
        return results
    
    def add_recipe_to_meal_plan(self, user_id: str, plan_date: date, meal_type: str,
                               recipe: Recipe, servings: Decimal) -> MealPlanEntry:
        """
        Add recipe to meal plan with specified servings.
        
        Args:
            user_id: ID of the user
            plan_date: Date for the meal
            meal_type: Type of meal
            recipe: Recipe to add
            servings: Number of servings
            
        Returns:
            Meal plan entry for the recipe
        """
        # Calculate calories and macros
        calories = int(recipe.calories_per_serving * servings)
        
        # Estimate macros (simplified - would use recipe database in real app)
        protein, carbs, fats = self._estimate_recipe_macros(recipe, servings)
        
        return MealPlanEntry(
            date=plan_date,
            meal_type=meal_type,
            item_type="recipe",
            recipe=recipe,
            servings=servings,
            calories=calories,
            protein_grams=protein,
            carb_grams=carbs,
            fat_grams=fats
        )
    
    def add_food_item_to_meal_plan(self, user_id: str, plan_date: date, meal_type: str,
                                  food_item: FoodItem, quantity: Decimal) -> MealPlanEntry:
        """
        Add individual food item to meal plan.
        
        Args:
            user_id: ID of the user
            plan_date: Date for the meal
            meal_type: Type of meal
            food_item: Food item to add
            quantity: Quantity of the food item
            
        Returns:
            Meal plan entry for the food item
        """
        # Calculate calories and macros based on quantity
        calories = int(food_item.calories_per_unit * quantity)
        protein = food_item.protein_per_unit * quantity
        carbs = food_item.carbs_per_unit * quantity
        fats = food_item.fats_per_unit * quantity
        
        return MealPlanEntry(
            date=plan_date,
            meal_type=meal_type,
            item_type="food_item",
            food_item=food_item,
            quantity=quantity,
            calories=calories,
            protein_grams=protein,
            carb_grams=carbs,
            fat_grams=fats
        )
    
    def calculate_recipe_meal_coverage(self, recipe: Recipe, servings_made: Decimal,
                                     target_calories_per_meal: int) -> Dict[str, any]:
        """
        Calculate how many whole meals a recipe will provide given servings made.
        
        Args:
            recipe: Recipe being made
            servings_made: Number of servings being prepared
            target_calories_per_meal: Target calories per meal
            
        Returns:
            Dict with meal coverage information
        """
        total_calories = recipe.calories_per_serving * servings_made
        calories_per_serving = recipe.calories_per_serving
        
        # Calculate servings per meal to hit target calories
        servings_per_meal = Decimal(str(target_calories_per_meal / calories_per_serving))
        
        # Calculate how many WHOLE meals this will provide
        whole_meals_covered = int(servings_made / servings_per_meal)
        
        # Calculate how many days this will last (assuming 1 meal per day of this type)
        days_covered = whole_meals_covered
        
        # Calculate leftover servings after whole meals
        leftover_servings = servings_made - (whole_meals_covered * servings_per_meal)
        
        return {
            "total_calories": int(total_calories),
            "whole_meals_covered": whole_meals_covered,
            "days_covered": days_covered,
            "servings_per_meal": float(servings_per_meal),
            "calories_per_serving": calories_per_serving,
            "leftover_servings": float(leftover_servings),
            "leftover_calories": int(leftover_servings * calories_per_serving)
        }
    
    def create_daily_meal_plan_from_entries(self, user_id: str, target_date: date,
                                          target_calories: int, 
                                          meal_entries: List[MealPlanEntry]) -> DailyMealPlan:
        """
        Create daily meal plan from user-selected meal entries.
        
        Args:
            user_id: ID of the user
            target_date: Date for the meal plan
            target_calories: Target calories for the day
            meal_entries: List of meal entries added by user
            
        Returns:
            Complete daily meal plan
        """
        total_calories = sum(entry.calories for entry in meal_entries)
        total_protein = sum(entry.protein_grams for entry in meal_entries)
        total_carbs = sum(entry.carb_grams for entry in meal_entries)
        total_fats = sum(entry.fat_grams for entry in meal_entries)
        
        return DailyMealPlan(
            date=target_date,
            user_id=user_id,
            target_calories=target_calories,
            meals=meal_entries,
            total_calories=total_calories,
            total_protein=total_protein,
            total_carbs=total_carbs,
            total_fats=total_fats,
            calories_remaining=target_calories - total_calories
        )
    
    def generate_comprehensive_grocery_list(self, daily_plans: List[DailyMealPlan],
                                           household_inventory: List[InventoryItem]) -> List[GroceryListItem]:
        """
        Generate comprehensive grocery list including recipes AND individual food items.
        
        Args:
            daily_plans: List of daily meal plans
            household_inventory: Current household inventory
            
        Returns:
            Complete grocery list for recipes and planned individual foods
        """
        # Collect recipes and their total servings needed
        recipe_servings = {}
        individual_foods = {}
        
        for daily_plan in daily_plans:
            for meal in daily_plan.meals:
                if meal.item_type == "recipe" and meal.recipe:
                    recipe_name = meal.recipe.name
                    if recipe_name in recipe_servings:
                        recipe_servings[recipe_name] = (
                            meal.recipe,
                            recipe_servings[recipe_name][1] + meal.servings
                        )
                    else:
                        recipe_servings[recipe_name] = (meal.recipe, meal.servings)
                
                elif meal.item_type == "food_item" and meal.food_item:
                    # Aggregate individual food items for grocery list
                    food_name = meal.food_item.name
                    if food_name in individual_foods:
                        individual_foods[food_name] = (
                            meal.food_item,
                            individual_foods[food_name][1] + meal.quantity
                        )
                    else:
                        individual_foods[food_name] = (meal.food_item, meal.quantity)
        
        # Generate grocery list for recipes
        recipe_grocery_items = []
        if recipe_servings:
            recipes_needed = list(recipe_servings.values())
            recipe_grocery_items = self._generate_household_grocery_list(recipes_needed, household_inventory)
        
        # Add individual food items to grocery list
        food_grocery_items = []
        for food_name, (food_item, total_quantity) in individual_foods.items():
            # Create grocery list item for individual foods
            display_amount = f"{total_quantity} {food_item.unit}"
            food_grocery_items.append(GroceryListItem(
                name=food_item.name,
                display_amount=display_amount,
                actual_need=display_amount,
                unit=food_item.unit
            ))
        
        # Combine recipe ingredients and individual foods
        return recipe_grocery_items + food_grocery_items
    
    def _estimate_recipe_macros(self, recipe: Recipe, servings: Decimal) -> Tuple[Decimal, Decimal, Decimal]:
        """
        Estimate macros for recipe and servings (simplified implementation).
        
        Args:
            recipe: Recipe to estimate macros for
            servings: Number of servings
            
        Returns:
            Tuple of (protein_grams, carb_grams, fat_grams)
        """
        # Simplified macro estimation based on calories
        total_calories = recipe.calories_per_serving * servings
        
        # Rough estimates: 30% protein, 40% carbs, 30% fat
        protein_calories = total_calories * Decimal('0.30')
        carb_calories = total_calories * Decimal('0.40')
        fat_calories = total_calories * Decimal('0.30')
        
        # Convert to grams (protein: 4 cal/g, carbs: 4 cal/g, fat: 9 cal/g)
        protein_grams = protein_calories / 4
        carb_grams = carb_calories / 4
        fat_grams = fat_calories / 9
        
        return protein_grams, carb_grams, fat_grams
    
    def _generate_household_grocery_list(self, recipes_needed: List[Tuple[Recipe, Decimal]],
                                       household_inventory: List[InventoryItem]) -> List[GroceryListItem]:
        """
        Generate consolidated grocery list for household meal plans.
        
        Args:
            recipes_needed: List of (recipe, servings) tuples
            household_inventory: Current household inventory
            
        Returns:
            Consolidated grocery list
        """
        # Scale recipes to needed servings and aggregate ingredients
        scaled_recipes = []
        scale_factors = {}
        
        for recipe, servings_needed in recipes_needed:
            # Calculate scale factor for this recipe instance
            scale_factor = servings_needed / recipe.base_servings
            scale_factors[recipe.name] = scale_factor
            scaled_recipes.append(recipe)
        
        # Use existing grocery list generation logic
        aggregated = self._aggregator.aggregate_with_practical_scaling(
            scaled_recipes, scale_factors, self._scaler
        )
        
        # Subtract household inventory
        net_needs = self._inventory_service.subtract_inventory(aggregated, household_inventory)
        
        # Convert to display units
        grocery_items = self._converter.convert_to_display_units(net_needs)
        
        return grocery_items
