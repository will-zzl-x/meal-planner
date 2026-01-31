"""
Inventory repository interface for household inventory management.
"""
from abc import ABC, abstractmethod
from typing import List
from ..domain.models import InventoryItem

class IInventoryRepository(ABC):
    """Interface for inventory data access operations."""
    
    @abstractmethod
    def get_household_inventory(self, household_id: str) -> List[InventoryItem]:
        """
        Get all inventory items for a household.
        
        Args:
            household_id: ID of the household
            
        Returns:
            List of household's inventory items
        """
        pass
    
    @abstractmethod
    def update_household_inventory(self, household_id: str, items: List[InventoryItem]) -> None:
        """
        Update household's complete inventory.
        
        Args:
            household_id: ID of the household
            items: Complete list of inventory items
        """
        pass
    
    @abstractmethod
    def add_inventory_item(self, household_id: str, item: InventoryItem) -> InventoryItem:
        """
        Add or update a single inventory item for household.
        
        Args:
            household_id: ID of the household
            item: Inventory item to add/update
            
        Returns:
            Added/updated inventory item
        """
        pass
    
    @abstractmethod
    def remove_inventory_item(self, household_id: str, ingredient_name: str, unit: str) -> bool:
        """
        Remove an inventory item from household.
        
        Args:
            household_id: ID of the household
            ingredient_name: Name of the ingredient
            unit: Unit of measurement
            
        Returns:
            True if removed, False if not found
        """
        pass
    
    @abstractmethod
    def clear_household_inventory(self, household_id: str) -> None:
        """
        Clear all inventory for a household.
        
        Args:
            household_id: ID of the household
        """
        pass
