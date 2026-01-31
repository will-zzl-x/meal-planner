"""
Service for inventory management and subtraction.
Extracted from monolithic GroceryListGenerator.
"""
from decimal import Decimal
from typing import Dict, List
from ..domain.models import InventoryItem

class InventoryService:
    """Handles inventory operations and subtraction from shopping needs."""
    
    def subtract_inventory(self, needed_ingredients: Dict[str, Decimal], 
                          inventory: List[InventoryItem]) -> Dict[str, Decimal]:
        """
        Subtract available inventory from needed ingredients.
        
        Args:
            needed_ingredients: Dict mapping "ingredient_name_unit" to needed quantity
            inventory: List of available inventory items
            
        Returns:
            Dict of net ingredients needed after subtracting inventory
        """
        net_needs = needed_ingredients.copy()
        
        for item in inventory:
            key = f"{item.name}_{item.unit}"
            if key in net_needs:
                net_needs[key] -= item.quantity
                if net_needs[key] <= 0:
                    del net_needs[key]
                    
        return net_needs
    
    def get_inventory_coverage(self, needed_ingredients: Dict[str, Decimal], 
                             inventory: List[InventoryItem]) -> Dict[str, Decimal]:
        """
        Calculate how much of each needed ingredient is covered by inventory.
        
        Args:
            needed_ingredients: Dict mapping "ingredient_name_unit" to needed quantity
            inventory: List of available inventory items
            
        Returns:
            Dict mapping ingredient keys to coverage percentage (0.0 to 1.0)
        """
        coverage = {}
        
        for key, needed_qty in needed_ingredients.items():
            name, unit = key.rsplit('_', 1)
            
            # Find matching inventory item
            available_qty = Decimal('0')
            for item in inventory:
                if item.name == name and item.unit == unit:
                    available_qty = item.quantity
                    break
            
            if needed_qty > 0:
                coverage[key] = min(Decimal('1'), available_qty / needed_qty)
            else:
                coverage[key] = Decimal('1')  # Fully covered if nothing needed
                
        return coverage
