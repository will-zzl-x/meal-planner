"""
Service layer for ingredient aggregation.
Extracted from monolithic GroceryListGenerator.
"""
from decimal import Decimal
from typing import Dict, List
from ..domain.models import Recipe, Ingredient

class IngredientAggregator:
    """Aggregates ingredients across multiple recipes."""
    
    def aggregate_with_serving_adjustments(self, recipes: List[Recipe], 
                                         serving_adjustments: Dict[str, int]) -> Dict[str, Decimal]:
        """
        Aggregate ingredients with serving count adjustments (ingredients stay the same).
        
        Args:
            recipes: List of recipes to aggregate
            serving_adjustments: New serving counts per recipe name
            
        Returns:
            Dict mapping "ingredient_name_unit" to total quantity needed
        """
        aggregated = {}
        
        for recipe in recipes:
            # Ingredients don't change - we just make fewer/more servings
            for ingredient in recipe.ingredients:
                key = f"{ingredient.name}_{ingredient.unit}"
                
                if key in aggregated:
                    aggregated[key] += ingredient.quantity
                else:
                    aggregated[key] = ingredient.quantity
                    
        return aggregated
    
    def aggregate(self, recipes: List[Recipe], scale_factors: Dict[str, Decimal] = None) -> Dict[str, Decimal]:
        """
        Aggregate ingredients across recipes with optional scaling (legacy method).
        
        Args:
            recipes: List of recipes to aggregate
            scale_factors: Optional scaling factors per recipe name
            
        Returns:
            Dict mapping "ingredient_name_unit" to total quantity
        """
        if scale_factors is None:
            scale_factors = {}
            
        aggregated = {}
        
        for recipe in recipes:
            scale_factor = scale_factors.get(recipe.name, Decimal('1'))
            
            for ingredient in recipe.ingredients:
                key = f"{ingredient.name}_{ingredient.unit}"
                scaled_quantity = ingredient.quantity * scale_factor
                
                if key in aggregated:
                    aggregated[key] += scaled_quantity
                else:
                    aggregated[key] = scaled_quantity
                    
        return aggregated
