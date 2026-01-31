from dataclasses import dataclass
from typing import Dict, List
from decimal import Decimal
from .security import (
    validate_ingredient_name, validate_recipe_name, validate_quantity,
    validate_unit, validate_servings, validate_calories, SecurityValidationError
)

@dataclass
class Ingredient:
    name: str
    quantity: Decimal
    unit: str
    
    def __post_init__(self):
        """Validate ingredient data on creation."""
        self.name = validate_ingredient_name(self.name)
        self.quantity = validate_quantity(self.quantity)
        self.unit = validate_unit(self.unit)

@dataclass
class Recipe:
    name: str
    ingredients: List[Ingredient]
    base_servings: int
    calories_per_serving: int
    
    def __post_init__(self):
        """Validate recipe data on creation."""
        self.name = validate_recipe_name(self.name)
        self.base_servings = validate_servings(self.base_servings)
        self.calories_per_serving = validate_calories(self.calories_per_serving)
        
        # Validate ingredients list
        if not self.ingredients:
            raise SecurityValidationError("Recipe must have at least one ingredient")

@dataclass
class InventoryItem:
    name: str
    quantity: Decimal
    unit: str
    
    def __post_init__(self):
        """Validate inventory item data on creation."""
        self.name = validate_ingredient_name(self.name)
        self.quantity = validate_quantity(self.quantity)
        self.unit = validate_unit(self.unit)

@dataclass
class StoreProfile:
    name: str
    item_sizes: Dict[str, str]  # e.g., {"onion_medium": "8 oz", "chicken_breast": "12 oz"}
    
    def __post_init__(self):
        """Validate store profile data on creation."""
        self.name = validate_recipe_name(self.name)  # Same validation as recipe names

@dataclass
class GroceryListItem:
    name: str
    display_amount: str
    actual_need: str
    unit: str
