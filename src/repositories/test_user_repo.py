#!/usr/bin/env python3
"""
Test the User Repository implementation.
"""
import sys
import os
from decimal import Decimal

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import directly with relative paths
import sqlite3
import uuid
from typing import Optional
from core.interfaces.user_repository import UserProfile
from database_manager import DatabaseManager

def test_user_repository():
    """Test user repository CRUD operations."""
    print("🧪 Testing User Repository")
    print("=" * 30)
    
    # Use test database
    repo = SQLiteUserRepository("test_meal_planner.db")
    
    # Test 1: Create user
    print("1. Creating user...")
    user = repo.create_user("John Doe", "john@example.com")
    print(f"   ✅ Created user: {user.name} (ID: {user.user_id[:8]}...)")
    
    # Test 2: Find by ID
    print("2. Finding user by ID...")
    found_user = repo.find_by_id(user.user_id)
    if found_user and found_user.name == "John Doe":
        print(f"   ✅ Found user: {found_user.name}")
    else:
        print("   ❌ User not found")
        return
    
    # Test 3: Find by email
    print("3. Finding user by email...")
    found_by_email = repo.find_by_email("john@example.com")
    if found_by_email and found_by_email.user_id == user.user_id:
        print(f"   ✅ Found user by email: {found_by_email.name}")
    else:
        print("   ❌ User not found by email")
        return
    
    # Test 4: Update profile
    print("4. Updating user profile...")
    user.current_weight = Decimal("180.5")
    user.body_fat_percentage = Decimal("15.0")
    user.daily_calorie_target = 2000
    
    updated_user = repo.update_profile(user)
    if updated_user.current_weight == Decimal("180.5"):
        print(f"   ✅ Updated profile: {updated_user.current_weight} lbs, {updated_user.body_fat_percentage}% BF")
    else:
        print("   ❌ Profile update failed")
        return
    
    # Test 5: Verify update persisted
    print("5. Verifying update persisted...")
    reloaded_user = repo.find_by_id(user.user_id)
    if reloaded_user and reloaded_user.current_weight == Decimal("180.5"):
        print(f"   ✅ Update persisted: {reloaded_user.current_weight} lbs")
    else:
        print("   ❌ Update did not persist")
        return
    
    # Test 6: Delete user
    print("6. Deleting user...")
    deleted = repo.delete_user(user.user_id)
    if deleted:
        print("   ✅ User deleted successfully")
    else:
        print("   ❌ User deletion failed")
        return
    
    # Test 7: Verify deletion
    print("7. Verifying deletion...")
    deleted_user = repo.find_by_id(user.user_id)
    if deleted_user is None:
        print("   ✅ User successfully removed from database")
    else:
        print("   ❌ User still exists after deletion")
        return
    
    print("\n🎉 All tests passed! User Repository is working correctly.")
    
    # Clean up test database
    os.remove("test_meal_planner.db")
    print("🧹 Test database cleaned up.")

if __name__ == "__main__":
    test_user_repository()
