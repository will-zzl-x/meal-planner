"""
Repository interfaces for data access abstraction.
Enables swapping storage implementations without changing business logic.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from ..domain.models import Recipe, InventoryItem

class IRecipeRepository(ABC):
    """Interface for recipe data access operations."""
    
    @abstractmethod
    def save(self, recipe: Recipe, household_id: str, created_by_user_id: str) -> Recipe:
        """
        Save a recipe for a household.
        
        Args:
            recipe: Recipe to save
            household_id: ID of the household that owns the recipe
            created_by_user_id: ID of the user who created the recipe
            
        Returns:
            Saved recipe with any generated IDs
        """
        pass
    
    @abstractmethod
    def find_by_id(self, recipe_id: str, household_id: str) -> Optional[Recipe]:
        """
        Find a recipe by ID for a specific household.
        
        Args:
            recipe_id: ID of the recipe
            household_id: ID of the household that owns the recipe
            
        Returns:
            Recipe if found, None otherwise
        """
        pass
    
    @abstractmethod
    def find_all_by_household(self, household_id: str) -> List[Recipe]:
        """
        Find all recipes for a specific household.
        
        Args:
            household_id: ID of the household
            
        Returns:
            List of household's recipes
        """
        pass
    
    @abstractmethod
    def delete(self, recipe_id: str, household_id: str) -> bool:
        """
        Delete a recipe for a specific household.

        Args:
            recipe_id: ID of the recipe to delete
            household_id: ID of the household that owns the recipe

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    def update(self, recipe: Recipe, household_id: str) -> Optional[Recipe]:
        """
        Replace an existing recipe's fields and ingredients.

        The recipe must have its `id` set; only recipes belonging to
        `household_id` are updated.

        Returns the persisted recipe, or None if no row matched.
        """
        pass
    
    @abstractmethod
    def find_by_name(self, name: str, household_id: str) -> Optional[Recipe]:
        """
        Find a recipe by name for a specific household.
        
        Args:
            name: Name of the recipe
            household_id: ID of the household that owns the recipe
            
        Returns:
            Recipe if found, None otherwise
        """
        pass
