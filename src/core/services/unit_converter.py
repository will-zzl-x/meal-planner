"""
Service for unit conversion and display formatting.
Extracted from monolithic GroceryListGenerator.
"""
from decimal import Decimal
from typing import Dict, List
import math
from ..domain.models import GroceryListItem

class UnitConverter:
    """Handles unit conversions and display formatting."""
    
    def __init__(self):
        # Items that should be displayed as whole units
        self.whole_items = {
            'onion': {'unit': 'medium', 'conversion': Decimal('8')},  # 1 medium = 8 oz
            'garlic': {'unit': 'cloves', 'conversion': Decimal('0.1')},  # 1 clove = 0.1 oz
            'bell_pepper': {'unit': 'medium', 'conversion': Decimal('6')},  # 1 medium = 6 oz
            'shallot': {'unit': 'medium', 'conversion': Decimal('2')},  # 1 medium = 2 oz
        }
    
    def convert_to_display_units(self, ingredient_quantities: Dict[str, Decimal]) -> List[GroceryListItem]:
        """
        Convert ingredient quantities to appropriate display units.
        
        Args:
            ingredient_quantities: Dict mapping "ingredient_name_unit" to quantity
            
        Returns:
            List of GroceryListItem with appropriate display formatting
        """
        grocery_items = []
        
        for key, quantity in ingredient_quantities.items():
            name, unit = key.rsplit('_', 1)
            
            if name in self.whole_items and unit == 'oz':
                # Convert to whole items
                item_info = self.whole_items[name]
                needed_items = quantity / item_info['conversion']
                display_count = math.ceil(float(needed_items))  # Round up for whole items
                
                display_amount = f"{display_count} {item_info['unit']}"
                actual_need = f"{needed_items:.1f} {item_info['unit']}"
                
                grocery_items.append(GroceryListItem(
                    name=name.replace('_', ' ').title(),
                    display_amount=display_amount,
                    actual_need=actual_need,
                    unit=item_info['unit']
                ))
            else:
                # Keep as weight/volume
                display_amount = f"{quantity:.1f} {unit}"
                grocery_items.append(GroceryListItem(
                    name=name.replace('_', ' ').title(),
                    display_amount=display_amount,
                    actual_need=display_amount,
                    unit=unit
                ))
                
        return grocery_items
    
    def add_conversion_rule(self, ingredient_name: str, unit: str, conversion_factor: Decimal):
        """
        Add new conversion rule for whole items.
        
        Args:
            ingredient_name: Name of ingredient
            unit: Display unit (e.g., 'medium', 'cloves')
            conversion_factor: How many oz per unit
        """
        self.whole_items[ingredient_name] = {
            'unit': unit,
            'conversion': conversion_factor
        }
