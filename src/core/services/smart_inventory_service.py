"""
Smart Inventory Management Service.
Tracks expiration dates, suggests recipes for expiring items, optimizes shopping.
"""
import sys
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from datetime import date, timedelta
from dataclasses import dataclass
from pathlib import Path

# Import from core layer
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.domain.models import InventoryItem  # noqa: F401  (re-exported for legacy callers)

@dataclass
class ShoppingOptimization:
    """Shopping list optimization results."""
    optimized_list: Dict[str, Decimal]
    cost_savings: Decimal
    waste_reduction: List[str]
    bulk_opportunities: List[str]

class SmartInventoryService:
    """Service for intelligent inventory management and optimization."""
    
    def __init__(self):
        # Default shelf life for common ingredients (days)
        self.default_shelf_life = {
            "chicken breast": 3,
            "salmon fillet": 2,
            "ground beef": 2,
            "milk": 7,
            "eggs": 21,
            "bread": 5,
            "bananas": 5,
            "apples": 14,
            "lettuce": 7,
            "tomatoes": 7,
            "onions": 30,
            "potatoes": 60,
            "rice": 365,
            "pasta": 730,
            "olive oil": 730,
            "flour": 365
        }
        
        # Storage location recommendations
        self.storage_locations = {
            "fridge": ["chicken breast", "salmon fillet", "milk", "eggs", "lettuce"],
            "freezer": ["ground beef", "bread"],
            "pantry": ["rice", "pasta", "flour", "olive oil", "onions", "potatoes"]
        }
    
    def add_inventory_item(self, name: str, quantity: Decimal, unit: str,
                          purchase_date: date = None, expiration_date: date = None) -> InventoryItem:
        """
        Add item to inventory with smart expiration date calculation.
        
        Args:
            name: Ingredient name
            quantity: Amount purchased
            unit: Unit of measurement
            purchase_date: When item was purchased (defaults to today)
            expiration_date: Known expiration date (optional)
            
        Returns:
            InventoryItem with calculated expiration and storage location
        """
        if purchase_date is None:
            purchase_date = date.today()
        
        # Calculate expiration date if not provided
        if expiration_date is None and name.lower() in self.default_shelf_life:
            shelf_life = self.default_shelf_life[name.lower()]
            expiration_date = purchase_date + timedelta(days=shelf_life)
        
        # Determine optimal storage location
        location = "pantry"  # default
        for storage, items in self.storage_locations.items():
            if name.lower() in items:
                location = storage
                break
        
        return InventoryItem(
            name=name,
            quantity=quantity,
            unit=unit,
            expiration_date=expiration_date,
            purchase_date=purchase_date,
            location=location
        )
    
    def get_expiring_items(self, inventory: List[InventoryItem], 
                          days_ahead: int = 3) -> List[InventoryItem]:
        """Get items expiring within specified days."""
        expiring = []
        cutoff_date = date.today() + timedelta(days=days_ahead)
        
        for item in inventory:
            if item.expiration_date and item.expiration_date <= cutoff_date:
                expiring.append(item)
        
        # Sort by expiration date (soonest first)
        expiring.sort(key=lambda x: x.expiration_date or date.max)
        return expiring
    
    def suggest_recipes_for_expiring_items(self, expiring_items: List[InventoryItem],
                                         available_recipes: List[Dict]) -> List[Dict]:
        """
        Suggest recipes that use expiring ingredients.
        
        Args:
            expiring_items: Items expiring soon
            available_recipes: User's recipe collection
            
        Returns:
            List of recipes prioritized by expiring ingredient usage
        """
        expiring_names = {item.name.lower() for item in expiring_items}
        recipe_scores = []
        
        for recipe in available_recipes:
            score = 0
            matching_ingredients = []
            
            # Check recipe ingredients against expiring items
            for ingredient in recipe.get("ingredients", []):
                ingredient_name = ingredient["name"].lower()
                if ingredient_name in expiring_names:
                    score += 1
                    matching_ingredients.append(ingredient_name)
            
            if score > 0:
                recipe_scores.append({
                    "recipe": recipe,
                    "expiring_ingredient_count": score,
                    "matching_ingredients": matching_ingredients,
                    "priority": "high" if score >= 2 else "medium"
                })
        
        # Sort by number of expiring ingredients used
        recipe_scores.sort(key=lambda x: x["expiring_ingredient_count"], reverse=True)
        return recipe_scores
    
    def optimize_shopping_list(self, needed_items: Dict[str, Decimal],
                             current_inventory: List[InventoryItem],
                             user_tier: str = "free") -> ShoppingOptimization:
        """
        Optimize shopping list to reduce waste and save money.
        
        Args:
            needed_items: Items needed for meal plan
            current_inventory: Current inventory items
            user_tier: User subscription tier
            
        Returns:
            ShoppingOptimization with recommendations
        """
        optimized_list = needed_items.copy()
        waste_reduction = []
        bulk_opportunities = []
        cost_savings = Decimal("0")
        
        # Create inventory lookup
        inventory_lookup = {}
        for item in current_inventory:
            if item.name in inventory_lookup:
                inventory_lookup[item.name] += item.quantity
            else:
                inventory_lookup[item.name] = item.quantity
        
        # Basic optimization: subtract existing inventory
        for item_name, needed_qty in needed_items.items():
            available_qty = inventory_lookup.get(item_name, Decimal("0"))
            
            if available_qty > 0:
                if available_qty >= needed_qty:
                    # Have enough, don't buy any
                    optimized_list[item_name] = Decimal("0")
                    waste_reduction.append(f"Using existing {item_name} ({available_qty} available)")
                else:
                    # Buy only what's needed
                    optimized_list[item_name] = needed_qty - available_qty
                    waste_reduction.append(f"Reduced {item_name} purchase by {available_qty}")
        
        # Remove zero quantities
        optimized_list = {k: v for k, v in optimized_list.items() if v > 0}
        
        # Premium features
        if user_tier == "premium":
            # Bulk buying opportunities
            for item_name, qty in optimized_list.items():
                if qty >= Decimal("500") and item_name.lower() in ["rice", "pasta", "flour"]:
                    bulk_opportunities.append(f"Consider bulk buying {item_name} for 15% savings")
                    cost_savings += Decimal("2.50")  # Estimated savings
            
            # Smart substitutions for expiring items
            expiring = self.get_expiring_items(current_inventory, days_ahead=2)
            for item in expiring:
                if item.name in optimized_list:
                    waste_reduction.append(f"Use expiring {item.name} first (expires {item.expiration_date})")
        
        return ShoppingOptimization(
            optimized_list=optimized_list,
            cost_savings=cost_savings,
            waste_reduction=waste_reduction,
            bulk_opportunities=bulk_opportunities
        )
    
    def track_waste(self, inventory: List[InventoryItem]) -> Dict[str, any]:
        """
        Track food waste and provide insights.
        
        Returns:
            Waste tracking statistics and recommendations
        """
        expired_items = [item for item in inventory if item.is_expired]
        expiring_soon = [item for item in inventory if item.is_expiring_soon]
        
        # Calculate waste value (simplified)
        waste_value = Decimal("0")
        for item in expired_items:
            # Rough cost estimation
            estimated_cost_per_unit = {
                "chicken breast": Decimal("8.00"),  # per lb
                "salmon fillet": Decimal("12.00"),
                "milk": Decimal("3.50"),  # per gallon
                "eggs": Decimal("2.50"),  # per dozen
                "bread": Decimal("2.00")  # per loaf
            }
            
            unit_cost = estimated_cost_per_unit.get(item.name.lower(), Decimal("1.00"))
            waste_value += unit_cost * (item.quantity / 100)  # Rough calculation
        
        return {
            "expired_items": len(expired_items),
            "expiring_soon": len(expiring_soon),
            "estimated_waste_value": waste_value,
            "waste_items": [{"name": item.name, "quantity": item.quantity, 
                           "expired_days": abs(item.days_until_expiration or 0)} 
                          for item in expired_items],
            "recommendations": self._generate_waste_recommendations(expired_items, expiring_soon)
        }
    
    def _generate_waste_recommendations(self, expired_items: List[InventoryItem],
                                      expiring_soon: List[InventoryItem]) -> List[str]:
        """Generate recommendations to reduce waste."""
        recommendations = []
        
        if len(expired_items) > 0:
            recommendations.append(f"You have {len(expired_items)} expired items. Check expiration dates more frequently.")
        
        if len(expiring_soon) > 0:
            recommendations.append(f"{len(expiring_soon)} items expiring soon. Plan meals using these ingredients first.")
        
        # Category-specific advice
        expired_categories = {}
        for item in expired_items:
            category = self._get_item_category(item.name)
            expired_categories[category] = expired_categories.get(category, 0) + 1
        
        if expired_categories.get("produce", 0) > 2:
            recommendations.append("Consider buying smaller quantities of fresh produce more frequently.")
        
        if expired_categories.get("dairy", 0) > 1:
            recommendations.append("Check dairy expiration dates when meal planning.")
        
        return recommendations
    
    def _get_item_category(self, item_name: str) -> str:
        """Categorize inventory items."""
        produce = ["lettuce", "tomatoes", "bananas", "apples", "onions", "potatoes"]
        dairy = ["milk", "eggs", "cheese", "yogurt"]
        meat = ["chicken breast", "salmon fillet", "ground beef"]
        
        name_lower = item_name.lower()
        
        if any(p in name_lower for p in produce):
            return "produce"
        elif any(d in name_lower for d in dairy):
            return "dairy"
        elif any(m in name_lower for m in meat):
            return "meat"
        else:
            return "pantry"
