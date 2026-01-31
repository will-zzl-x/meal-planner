"""
Service for recipe scaling based on calorie targets.
Extracted from monolithic GroceryListGenerator.
"""
from decimal import Decimal
from typing import Dict, List
import math
from ..domain.models import Recipe, Ingredient

class RecipeScaler:
    """Handles calorie-based recipe scaling with practical rounding."""
    
    def __init__(self):
        # Define rounding rules for different ingredient types
        self.whole_items = {'garlic', 'onion', 'bell_pepper', 'shallot', 'lemon', 'lime'}
        self.liquid_units = {'tbsp', 'tsp'}
        self.powder_units = {'cup', 'oz'}  # Keep precise for flour, sugar, etc.
    
    def calculate_serving_adjustments(self, recipes: List[Recipe], calorie_targets: Dict[str, int]) -> Dict[str, int]:
        """
        Calculate new serving counts based on calorie targets (minimum per serving).
        
        Args:
            recipes: List of recipes to adjust
            calorie_targets: Target MINIMUM calories per serving for each recipe
            
        Returns:
            Dict mapping recipe name to new serving count
        """
        serving_adjustments = {}
        
        for recipe in recipes:
            if recipe.name in calorie_targets:
                target_min_calories = calorie_targets[recipe.name]
                total_recipe_calories = recipe.calories_per_serving * recipe.base_servings
                
                # Calculate how many servings at target calories
                ideal_servings = total_recipe_calories / target_min_calories
                
                # Round DOWN to ensure we meet minimum calorie requirement
                new_servings = max(1, int(ideal_servings))  # At least 1 serving
                
                serving_adjustments[recipe.name] = new_servings
            else:
                # No calorie target, keep original servings
                serving_adjustments[recipe.name] = recipe.base_servings
                
        return serving_adjustments
    
    def scale_recipe_ingredients(self, recipe: Recipe, scale_factor: Decimal) -> List[Ingredient]:
        """
        Scale recipe ingredients with practical rounding rules.
        
        Args:
            recipe: Recipe to scale
            scale_factor: Scaling factor to apply
            
        Returns:
            List of scaled ingredients with practical quantities
        """
        scaled_ingredients = []
        
        for ingredient in recipe.ingredients:
            scaled_quantity = ingredient.quantity * scale_factor
            practical_quantity = self._round_to_practical(
                ingredient.name, 
                ingredient.unit, 
                scaled_quantity
            )
            
            scaled_ingredients.append(Ingredient(
                name=ingredient.name,
                quantity=practical_quantity,
                unit=ingredient.unit
            ))
            
        return scaled_ingredients
    
    def _round_to_practical(self, ingredient_name: str, unit: str, quantity: Decimal) -> Decimal:
        """
        Round ingredient quantity to practical cooking amounts.
        
        Args:
            ingredient_name: Name of ingredient
            unit: Unit of measurement
            quantity: Scaled quantity
            
        Returns:
            Practically rounded quantity
        """
        # Whole items - round to practical amounts
        if ingredient_name in self.whole_items:
            if unit == 'cloves':  # Garlic cloves
                return Decimal(str(max(1, round(float(quantity)))))
            else:  # Onions, bell peppers, etc.
                # Round to nearest 0.5 for practical cutting
                rounded = round(float(quantity) * 2) / 2
                return Decimal(str(max(0.5, rounded)))
        
        # Liquid measurements - round to measurable increments
        elif unit in self.liquid_units:
            return self._round_liquid_measurement(quantity, unit)
        
        # Powders - keep precise
        elif unit in self.powder_units:
            return quantity  # Keep precise for baking accuracy
        
        # Default - round to 1 decimal place
        else:
            return Decimal(str(round(float(quantity), 1)))
    
    def _round_liquid_measurement(self, quantity: Decimal, unit: str) -> Decimal:
        """
        Round liquid measurements to practical increments.
        
        Args:
            quantity: Liquid quantity
            unit: Unit (tbsp or tsp)
            
        Returns:
            Rounded quantity to nearest practical measurement
        """
        qty_float = float(quantity)
        
        if unit == 'tsp':
            # Round to nearest 1/4 tsp
            increments = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]
            closest = min(increments, key=lambda x: abs(x - qty_float))
            return Decimal(str(closest))
        
        elif unit == 'tbsp':
            # Round to nearest 1/2 tbsp
            increments = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
            closest = min(increments, key=lambda x: abs(x - qty_float))
            return Decimal(str(closest))
        
        return quantity
    
    def get_adjusted_recipe_info(self, recipe: Recipe, new_servings: int) -> dict:
        """
        Get recipe information with adjusted serving count.
        
        Args:
            recipe: Original recipe
            new_servings: New serving count
            
        Returns:
            Dict with adjusted recipe information
        """
        total_calories = recipe.calories_per_serving * recipe.base_servings
        calories_per_serving = total_calories / new_servings if new_servings > 0 else 0
        
        return {
            'name': recipe.name,
            'original_servings': recipe.base_servings,
            'new_servings': new_servings,
            'original_calories_per_serving': recipe.calories_per_serving,
            'new_calories_per_serving': int(calories_per_serving),
            'ingredients': recipe.ingredients  # Ingredients stay the same!
        }
