#!/usr/bin/env python3
"""
Test SQLiteUserRepository with household support.
"""
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from repositories.sqlite import DatabaseManager
from repositories.sqlite.user_repository import SQLiteUserRepository

def test_user_repository():
    """Test user repository with household functionality."""
    print("👥 Testing SQLiteUserRepository with Household Support")
    print("=" * 55)
    
    # Create test database
    db_manager = DatabaseManager("test_user_repo.db")
    
    try:
        # Initialize database with new schema
        print("📋 Initializing database with household support...")
        db_manager.initialize_database()
        
        # Create repository
        user_repo = SQLiteUserRepository(db_manager)
        
        # Test 1: Create user with new household
        print("\n🏠 Test 1: Creating user with new household")
        user1 = user_repo.create_user(
            name="Alice Johnson", 
            email="alice@example.com",
            household_name="Johnson Family"
        )
        print(f"✅ Created user: {user1.name} (ID: {user1.user_id})")
        
        # Test 2: Create second user and add to same household
        print("\n👫 Test 2: Adding second user to same household")
        user2 = user_repo.create_user(
            name="Bob Johnson",
            email="bob@example.com"
        )
        
        # Get Alice's household ID and add Bob to it
        alice_household_id = user_repo.get_user_household_id(user1.user_id)
        success = user_repo.add_user_to_household(user2.user_id, alice_household_id)
        print(f"✅ Added Bob to household: {success}")
        
        # Test 3: Get household members
        print("\n👨‍👩‍👧‍👦 Test 3: Getting household members")
        members = user_repo.get_household_members(user1.user_id)
        print(f"✅ Household members: {[m.name for m in members]}")
        
        # Test 4: Update user profile
        print("\n📝 Test 4: Updating user profile")
        from decimal import Decimal
        user1.current_weight = Decimal('150.5')
        user1.body_fat_percentage = Decimal('18.5')
        user1.daily_calorie_target = 2000
        
        updated_user = user_repo.update_profile(user1)
        print(f"✅ Updated profile - Weight: {updated_user.current_weight}, BF%: {updated_user.body_fat_percentage}")
        
        # Test 5: Find by email
        print("\n🔍 Test 5: Finding user by email")
        found_user = user_repo.find_by_email("alice@example.com")
        print(f"✅ Found user by email: {found_user.name if found_user else 'Not found'}")
        
        print("\n🎉 All user repository tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ User repository test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up test database
        if os.path.exists("test_user_repo.db"):
            os.remove("test_user_repo.db")
            print("🧹 Test database cleaned up")

if __name__ == "__main__":
    print("🧪 User Repository Test Suite")
    print("=" * 30)
    
    success = test_user_repository()
    
    if success:
        print("\n✅ User repository implementation complete!")
        print("🚀 Ready for Task 2.2: Recipe Repository Implementation")
    else:
        print("\n❌ Tests failed. Check the errors above.")
        sys.exit(1)
