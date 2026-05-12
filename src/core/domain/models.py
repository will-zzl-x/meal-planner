from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional
from .security import (
    validate_ingredient_name, validate_recipe_name, validate_quantity,
    validate_unit, validate_servings, validate_calories, SecurityValidationError
)

@dataclass
class Ingredient:
    name: str
    quantity: Decimal
    unit: str
    store: Optional[str] = None  # Where to buy this (e.g., "Costco", "Walmart"); None = unspecified.
    # Slice 8b: when the user picks an ingredient from the food-database
    # search picker, we record which catalog row it came from and how many
    # of that catalog row's servings the recipe uses. Calories are then a
    # straight multiplication (servings × catalog.calories_per_serving)
    # instead of a guess from a free-text name. Old/seed/scaler-built
    # ingredients leave these as None.
    catalog_ingredient_id: Optional[str] = None
    servings: Optional[Decimal] = None

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
    id: Optional[str] = None  # Populated by repository reads; None for unsaved.
    instructions: List[str] = field(default_factory=list)  # Step-by-step cooking directions.
    notes: Optional[str] = None  # Free-form context (source, tweaks, status flags).
    tier: Optional[str] = None   # Personal rating: "S" / "A" / "B" / "C" / "D" / "E" / None.

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
    expiration_date: Optional[date] = None
    purchase_date: Optional[date] = None
    location: str = "pantry"  # pantry, fridge, freezer
    # V2-2: optional reference to the catalog row this pantry item
    # represents. When set, pantry-coverage matching can be exact
    # (catalog_ingredient_id == catalog_ingredient_id) instead of doing
    # fuzzy name comparison. Legacy / quick-typed items leave it None.
    catalog_ingredient_id: Optional[str] = None

    def __post_init__(self):
        """Validate inventory item data on creation."""
        self.name = validate_ingredient_name(self.name)
        self.quantity = validate_quantity(self.quantity)
        self.unit = validate_unit(self.unit)

    @property
    def days_until_expiration(self) -> Optional[int]:
        if not self.expiration_date:
            return None
        return (self.expiration_date - date.today()).days

    @property
    def is_expiring_soon(self) -> bool:
        days = self.days_until_expiration
        return days is not None and days <= 3

    @property
    def is_expired(self) -> bool:
        days = self.days_until_expiration
        return days is not None and days < 0

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


@dataclass
class FoodItem:
    """Individual food item (not a recipe).

    Macros and calories are expressed per `unit` (e.g. per piece, per scoop, per 100g).
    Source-tracking fields are optional so this also covers the simpler "planned meal"
    shape used by the meal planner.
    """
    name: str
    calories_per_unit: int
    protein_per_unit: Decimal
    carbs_per_unit: Decimal
    fats_per_unit: Decimal
    unit: str
    category: str  # "food" or "restaurant"
    source: Optional[str] = None      # Which database provided this item
    food_id: Optional[str] = None     # Original database ID
    brand: Optional[str] = None


@dataclass
class CatalogIngredient:
    """An ingredient cached locally from a real food database (USDA, Open
    Food Facts) or entered manually. Calories and macros are expressed per
    one `serving_label` (e.g. "1 large egg", "1 cup", "100g") — the unit
    the source database reported them in.
    """
    id: str
    name: str
    serving_label: str
    calories_per_serving: int
    protein_per_serving: Decimal = Decimal("0")
    carbs_per_serving: Decimal = Decimal("0")
    fat_per_serving: Decimal = Decimal("0")
    brand: Optional[str] = None
    source: Optional[str] = None      # "usda" | "openfoodfacts" | "manual"
    external_id: Optional[str] = None

    @property
    def display_name(self) -> str:
        """Brand-prefixed name for UI display (Chobani — Greek Yogurt 5%)."""
        return f"{self.brand} — {self.name}" if self.brand else self.name

    @classmethod
    def from_food_item(cls, item: "FoodItem") -> "CatalogIngredient":
        """Translate a food-DB search result into a catalog row ready to save.

        Used in two places: the picker UI (when the user clicks Add) and
        the seed recipe backfiller (when an automated match is found).
        """
        return cls(
            id="",
            name=item.name,
            serving_label=item.unit,
            calories_per_serving=int(item.calories_per_unit),
            protein_per_serving=item.protein_per_unit,
            carbs_per_serving=item.carbs_per_unit,
            fat_per_serving=item.fats_per_unit,
            brand=item.brand,
            source=item.source or "manual",
            external_id=item.food_id,
        )
