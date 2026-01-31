#!/usr/bin/env python3
"""
CLI Demo - Clean Architecture Implementation
Web layer that depends on core business logic only.
"""
from decimal import Decimal
import sys
import os

# Add src to path for Clean Architecture imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core import Recipe, Ingredient, InventoryItem, StoreProfile
from core import IngredientAggregator, RecipeScaler, UnitConverter, InventoryService

class GroceryListGenerator:
    """
    Orchestrates grocery list generation using Clean Architecture services.
    Web layer component that depends only on core business logic.
    """
    
    def __init__(self, store_profile: StoreProfile):
        self.store_profile = store_profile
        self._aggregator = IngredientAggregator()
        self._scaler = RecipeScaler()
        self._converter = UnitConverter()
        self._inventory_service = InventoryService()
        
    def generate_list(self, recipes, inventory, calorie_targets=None):
        """Generate grocery list with serving-based calorie targeting."""
        
        # Step 1: Calculate serving adjustments from calorie targets
        serving_adjustments = {}
        adjusted_recipes_info = []
        
        if calorie_targets:
            serving_adjustments = self._scaler.calculate_serving_adjustments(recipes, calorie_targets)
            
            # Get adjusted recipe information for display
            for recipe in recipes:
                new_servings = serving_adjustments.get(recipe.name, recipe.base_servings)
                adjusted_info = self._scaler.get_adjusted_recipe_info(recipe, new_servings)
                adjusted_recipes_info.append(adjusted_info)
        else:
            # No calorie targets, use original servings
            for recipe in recipes:
                serving_adjustments[recipe.name] = recipe.base_servings
                adjusted_recipes_info.append({
                    'name': recipe.name,
                    'original_servings': recipe.base_servings,
                    'new_servings': recipe.base_servings,
                    'original_calories_per_serving': recipe.calories_per_serving,
                    'new_calories_per_serving': recipe.calories_per_serving,
                    'ingredients': recipe.ingredients
                })
        
        # Step 2: Aggregate ingredients (ingredients don't change, just serving counts)
        aggregated = self._aggregator.aggregate_with_serving_adjustments(recipes, serving_adjustments)
        
        # Step 3: Subtract inventory
        net_needs = self._inventory_service.subtract_inventory(aggregated, inventory)
        
        # Step 4: Convert to appropriate display units
        grocery_items = self._converter.convert_to_display_units(net_needs)
        
        return grocery_items, adjusted_recipes_info

def create_sample_data():
    """Create sample recipes and inventory for testing."""
    
    # Sample recipes
    chicken_stir_fry = Recipe(
        name="Chicken Stir Fry",
        ingredients=[
            Ingredient("chicken_breast", Decimal('16'), "oz"),  # 1 lb
            Ingredient("bell_pepper", Decimal('6'), "oz"),      # 1 medium
            Ingredient("onion", Decimal('8'), "oz"),            # 1 medium
            Ingredient("garlic", Decimal('0.2'), "oz"),         # 2 cloves
        ],
        base_servings=4,
        calories_per_serving=350
    )
    
    chicken_soup = Recipe(
        name="Chicken Soup",
        ingredients=[
            Ingredient("chicken_breast", Decimal('8'), "oz"),   # 0.5 lb
            Ingredient("onion", Decimal('4'), "oz"),            # 0.5 medium
            Ingredient("garlic", Decimal('0.1'), "oz"),         # 1 clove
        ],
        base_servings=2,
        calories_per_serving=280
    )
    
    # Sample inventory
    inventory = [
        InventoryItem("chicken_breast", Decimal('4'), "oz"),    # Have 0.25 lb
        InventoryItem("onion", Decimal('8'), "oz"),             # Have 1 medium
    ]
    
    # Sample store profile
    store = StoreProfile(
        name="Generic Store",
        item_sizes={
            "onion_medium": "8 oz",
            "chicken_breast": "12 oz",
            "garlic_clove": "0.1 oz"
        }
    )
    
    return [chicken_stir_fry, chicken_soup], inventory, store

def demo_calorie_targeting():
    """Demonstrate calorie targeting feature."""
    recipes, inventory, store = create_sample_data()
    generator = GroceryListGenerator(store)
    
    print("🎯 Calorie Targeting Demo")
    print("=" * 30)
    
    # Original recipe
    print("Original Chicken Stir Fry: 4 servings at 350 cal each (1400 total calories)")
    
    # Target 500 calories MINIMUM per serving
    calorie_targets = {"Chicken Stir Fry": 500}
    
    # Generate list with calorie targeting
    grocery_list, adjusted_recipes = generator.generate_list([recipes[0]], inventory, calorie_targets)
    
    # Show the adjusted recipe info
    for recipe_info in adjusted_recipes:
        print(f"Adjusted: {recipe_info['new_servings']} servings at {recipe_info['new_calories_per_serving']} cal each")
        print(f"(Recipe ingredients stay the same - just make fewer servings)")
    
    print(f"\n🛒 Grocery List (same ingredients, different serving count):")
    for item in grocery_list:
        if item.display_amount != item.actual_need:
            print(f"  • {item.name}: {item.display_amount} (need {item.actual_need})")
        else:
            print(f"  • {item.name}: {item.display_amount}")

def main():
    print("🍽️  Meal Planning App - Clean Architecture Demo")
    print("=" * 50)
    
    # Create sample data
    recipes, inventory, store = create_sample_data()
    
    print("📋 Selected Recipes:")
    for recipe in recipes:
        print(f"  • {recipe.name} ({recipe.base_servings} servings, {recipe.calories_per_serving} cal/serving)")
    
    print(f"\n📦 Current Inventory:")
    for item in inventory:
        print(f"  • {item.name.replace('_', ' ').title()}: {item.quantity} {item.unit}")
    
    # Generate grocery list
    generator = GroceryListGenerator(store)
    grocery_list, recipe_info = generator.generate_list(recipes, inventory)
    
    print(f"\n🛒 Grocery List:")
    if not grocery_list:
        print("  Nothing to buy - you have everything!")
    else:
        for item in grocery_list:
            if item.display_amount != item.actual_need:
                print(f"  • {item.name}: {item.display_amount} (need {item.actual_need})")
            else:
                print(f"  • {item.name}: {item.display_amount}")
    
    print("\n" + "=" * 50)
    demo_calorie_targeting()

if __name__ == "__main__":
    main()
