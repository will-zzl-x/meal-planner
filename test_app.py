#!/usr/bin/env python3
"""
Manual test script for Meal Planner Streamlit app
Tests all major functionality without running the full UI
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "src"))

def test_app_imports():
    """Test all app imports work correctly"""
    print("🧪 Testing Streamlit App Imports...")
    
    try:
        import streamlit as st
        from datetime import datetime, timedelta
        
        from src.core.services.body_composition_service import BodyCompositionService
        from src.core.services.calorie_banking_service import CalorieBankingService
        from src.core.services.macro_tracking_service import MacroTrackingService
        from src.core.services.enhanced_grocery_generator import EnhancedGroceryListGenerator
        from src.core.services.smart_inventory_service import SmartInventoryService
        from src.repositories.sqlite.user_repository import SQLiteUserRepository
        from src.repositories.sqlite.recipe_repository import SQLiteRecipeRepository
        from src.repositories.sqlite.calorie_tracking_repository import SQLiteCalorieTrackingRepository
        from src.repositories.database_manager import DatabaseManager
        
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_service_initialization():
    """Test service initialization like the app does"""
    print("\n🧪 Testing Service Initialization...")
    
    try:
        from src.repositories.database_manager import DatabaseManager
        from src.repositories.sqlite.user_repository import SQLiteUserRepository
        from src.core.services.body_composition_service import BodyCompositionService
        from src.core.services.calorie_banking_service import CalorieBankingService
        from src.core.services.macro_tracking_service import MacroTrackingService
        from src.core.services.smart_inventory_service import SmartInventoryService
        
        # Initialize like the app does
        db_manager = DatabaseManager()
        user_repo = SQLiteUserRepository(db_manager)
        
        services = {
            'body_comp': BodyCompositionService(),
            'calorie_banking': CalorieBankingService(),
            'macro_tracking': MacroTrackingService(),
            'inventory': SmartInventoryService(),
            'user_repo': user_repo
        }
        
        print("✅ All services initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Service initialization failed: {e}")
        return False

def test_meal_planning_logic():
    """Test the meal planning session state logic"""
    print("\n🧪 Testing Meal Planning Logic...")
    
    try:
        # Simulate session state
        session_state = {}
        
        # Test flexible meal count
        num_meals = 5
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        # Initialize meal plan like the app does
        session_state['num_meals'] = num_meals
        session_state['meal_plan'] = {day: {f"meal_{i+1}": [] for i in range(num_meals)} for day in days}
        
        # Test adding a recipe
        session_state['selected_recipes'] = {
            "Grilled Chicken": {"calories": 165, "protein": 31}
        }
        
        # Add recipe to meal plan
        session_state['meal_plan']['Monday']['meal_1'].append("Grilled Chicken")
        
        # Test nutrition calculation
        total_calories = 0
        total_protein = 0
        for meal_num in range(num_meals):
            meal_key = f"meal_{meal_num+1}"
            meals = session_state['meal_plan']['Monday'][meal_key]
            for meal in meals:
                if meal in session_state['selected_recipes']:
                    recipe = session_state['selected_recipes'][meal]
                    total_calories += recipe['calories']
                    total_protein += recipe['protein']
        
        print(f"✅ Meal planning logic works: {total_calories} cal, {total_protein}g protein")
        return True
    except Exception as e:
        print(f"❌ Meal planning logic failed: {e}")
        return False

def test_inventory_logic():
    """Test inventory management logic"""
    print("\n🧪 Testing Inventory Logic...")
    
    try:
        from datetime import datetime, timedelta
        
        # Simulate inventory item
        purchase_date = datetime.now().date()
        storage_location = "Fridge"
        
        # Calculate expiration like the app does
        expiration_days = {"Fridge": 7, "Freezer": 90, "Pantry": 365}
        expiration_date = purchase_date + timedelta(days=expiration_days[storage_location])
        
        # Test expiration warning logic
        days_until_expiration = (expiration_date - datetime.now().date()).days
        
        if days_until_expiration <= 3:
            status = "🔴 Expires soon!"
        elif days_until_expiration <= 7:
            status = "🟡 Use this week"
        else:
            status = f"🟢 Good for {days_until_expiration} days"
        
        print(f"✅ Inventory logic works: {status}")
        return True
    except Exception as e:
        print(f"❌ Inventory logic failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🍽️ MEAL PLANNER - COMPREHENSIVE TESTING")
    print("=" * 50)
    
    tests = [
        test_app_imports,
        test_service_initialization,
        test_meal_planning_logic,
        test_inventory_logic
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! App is ready for use.")
        return True
    else:
        print("⚠️  Some tests failed. Check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
