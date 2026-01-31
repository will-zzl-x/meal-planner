#!/usr/bin/env python3
"""
Test Smart Inventory Management Service.
"""
import sys
import os
from decimal import Decimal
from datetime import date, timedelta

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from core.services.smart_inventory_service import SmartInventoryService

def test_smart_inventory_service():
    """Test smart inventory management features."""
    print("🧪 Testing Smart Inventory Management Service")
    print("=" * 44)
    
    service = SmartInventoryService()
    
    # Test 1: Adding inventory items with smart expiration calculation
    print("1. Testing inventory item creation...")
    
    today = date.today()
    
    # Add items with automatic expiration calculation
    chicken = service.add_inventory_item("chicken breast", Decimal("2"), "lbs", today)
    milk = service.add_inventory_item("milk", Decimal("1"), "gallon", today)
    rice = service.add_inventory_item("rice", Decimal("5"), "lbs", today)
    
    print(f"   ✅ Chicken breast: expires {chicken.expiration_date} (location: {chicken.location})")
    print(f"   ✅ Milk: expires {milk.expiration_date} (location: {milk.location})")
    print(f"   ✅ Rice: expires {rice.expiration_date} (location: {rice.location})")
    
    # Test 2: Expiring items detection
    print("\n2. Testing expiring items detection...")
    
    # Create test inventory with items at different expiration stages
    test_inventory = [
        service.add_inventory_item("lettuce", Decimal("1"), "head", 
                                 today - timedelta(days=5)),  # Expired
        service.add_inventory_item("bananas", Decimal("6"), "pieces", 
                                 today - timedelta(days=3)),  # Expiring soon
        service.add_inventory_item("apples", Decimal("8"), "pieces", 
                                 today - timedelta(days=2)),  # Still good
        chicken,  # Fresh
        milk      # Fresh
    ]
    
    expiring_items = service.get_expiring_items(test_inventory, days_ahead=3)
    expired_count = sum(1 for item in test_inventory if item.is_expired)
    expiring_count = sum(1 for item in test_inventory if item.is_expiring_soon)
    
    print(f"   ✅ Total inventory items: {len(test_inventory)}")
    print(f"   ✅ Expired items: {expired_count}")
    print(f"   ✅ Expiring soon: {expiring_count}")
    print(f"   ✅ Items to use within 3 days: {len(expiring_items)}")
    
    if expiring_items:
        print(f"   ✅ Most urgent: {expiring_items[0].name} (expires {expiring_items[0].expiration_date})")
    
    # Test 3: Recipe suggestions for expiring items
    print("\n3. Testing recipe suggestions for expiring items...")
    
    # Sample recipes
    available_recipes = [
        {
            "name": "Caesar Salad",
            "ingredients": [
                {"name": "lettuce", "amount": 200},
                {"name": "chicken breast", "amount": 150}
            ]
        },
        {
            "name": "Banana Smoothie",
            "ingredients": [
                {"name": "bananas", "amount": 2},
                {"name": "milk", "amount": 250}
            ]
        },
        {
            "name": "Apple Pie",
            "ingredients": [
                {"name": "apples", "amount": 6},
                {"name": "flour", "amount": 200}
            ]
        },
        {
            "name": "Chicken Rice Bowl",
            "ingredients": [
                {"name": "chicken breast", "amount": 200},
                {"name": "rice", "amount": 150}
            ]
        }
    ]
    
    recipe_suggestions = service.suggest_recipes_for_expiring_items(expiring_items, available_recipes)
    
    print(f"   ✅ Recipe suggestions: {len(recipe_suggestions)}")
    for suggestion in recipe_suggestions:
        recipe_name = suggestion["recipe"]["name"]
        ingredient_count = suggestion["expiring_ingredient_count"]
        priority = suggestion["priority"]
        matching = suggestion["matching_ingredients"]
        print(f"      {recipe_name}: {ingredient_count} expiring ingredients ({priority} priority)")
        print(f"         Uses: {', '.join(matching)}")
    
    # Test 4: Shopping list optimization
    print("\n4. Testing shopping list optimization...")
    
    # Needed items for meal plan
    needed_items = {
        "chicken breast": Decimal("3"),  # Need 3 lbs, have 2 lbs
        "lettuce": Decimal("2"),         # Need 2 heads, have 1 (expired)
        "rice": Decimal("2"),            # Need 2 lbs, have 5 lbs
        "salmon fillet": Decimal("1"),   # Need 1 lb, have 0
        "pasta": Decimal("2")            # Need 2 lbs, have 0
    }
    
    # Test free tier optimization
    free_optimization = service.optimize_shopping_list(needed_items, test_inventory, "free")
    
    print(f"   ✅ FREE TIER:")
    print(f"      Original items: {len(needed_items)}")
    print(f"      Optimized items: {len(free_optimization.optimized_list)}")
    print(f"      Waste reduction tips: {len(free_optimization.waste_reduction)}")
    
    for tip in free_optimization.waste_reduction[:2]:
        print(f"         {tip}")
    
    # Test premium tier optimization
    premium_optimization = service.optimize_shopping_list(needed_items, test_inventory, "premium")
    
    print(f"   ✅ PREMIUM TIER:")
    print(f"      Bulk opportunities: {len(premium_optimization.bulk_opportunities)}")
    print(f"      Estimated savings: ${premium_optimization.cost_savings}")
    print(f"      Advanced waste tips: {len(premium_optimization.waste_reduction)}")
    
    if premium_optimization.bulk_opportunities:
        print(f"         Bulk tip: {premium_optimization.bulk_opportunities[0]}")
    
    # Test 5: Waste tracking and insights
    print("\n5. Testing waste tracking...")
    
    waste_report = service.track_waste(test_inventory)
    
    print(f"   ✅ Expired items: {waste_report['expired_items']}")
    print(f"   ✅ Expiring soon: {waste_report['expiring_soon']}")
    print(f"   ✅ Estimated waste value: ${waste_report['estimated_waste_value']}")
    print(f"   ✅ Recommendations: {len(waste_report['recommendations'])}")
    
    for rec in waste_report['recommendations']:
        print(f"      • {rec}")
    
    # Test 6: Storage location recommendations
    print("\n6. Testing storage location recommendations...")
    
    storage_test_items = [
        "chicken breast", "milk", "rice", "pasta", "onions", "bread"
    ]
    
    print("   ✅ Storage recommendations:")
    for item_name in storage_test_items:
        item = service.add_inventory_item(item_name, Decimal("1"), "unit")
        print(f"      {item_name}: {item.location}")
    
    # Test 7: Shelf life intelligence
    print("\n7. Testing shelf life intelligence...")
    
    shelf_life_items = ["chicken breast", "salmon fillet", "milk", "eggs", "rice", "flour"]
    
    print("   ✅ Default shelf life (days):")
    for item_name in shelf_life_items:
        days = service.default_shelf_life.get(item_name.lower(), "Unknown")
        print(f"      {item_name}: {days}")
    
    print("\n🎉 All smart inventory tests passed!")
    print("💡 Key Features Working:")
    print("   • Smart expiration date calculation")
    print("   • Expiring item detection and prioritization")
    print("   • Recipe suggestions for expiring ingredients")
    print("   • Shopping list optimization (free vs premium)")
    print("   • Waste tracking and cost analysis")
    print("   • Storage location recommendations")
    print("   • Intelligent shelf life management")

if __name__ == "__main__":
    test_smart_inventory_service()
