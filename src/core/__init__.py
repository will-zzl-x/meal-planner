# Core Domain Package - Clean Architecture
# Business logic and domain models (innermost layer)

# Domain Models
from .domain.models import Recipe, Ingredient, InventoryItem, StoreProfile, GroceryListItem
from .domain.security import SecurityValidationError

# Business Services  
from .services import IngredientAggregator, RecipeScaler, UnitConverter, InventoryService

# Repository Interfaces (defined in core, implemented in outer layers)
from .interfaces import (
    IRecipeRepository, IUserRepository, IInventoryRepository, 
    ICalorieTrackingRepository, UserProfile, DailyCalorieLog, WeeklyCaloriePlan
)

__all__ = [
    # Domain Models
    'Recipe', 'Ingredient', 'InventoryItem', 'StoreProfile', 'GroceryListItem',
    'SecurityValidationError',
    
    # Business Services
    'IngredientAggregator', 'RecipeScaler', 'UnitConverter', 'InventoryService',
    
    # Repository Interfaces
    'IRecipeRepository', 'IUserRepository', 'IInventoryRepository', 
    'ICalorieTrackingRepository', 'UserProfile', 'DailyCalorieLog', 'WeeklyCaloriePlan'
]
