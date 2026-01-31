#!/usr/bin/env python3
"""
Database initialization test script.
Tests SQLite schema creation and migration system.
"""
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from repositories.sqlite import DatabaseManager

def test_database_initialization():
    """Test database initialization and schema creation."""
    print("🗄️  Testing Database Initialization")
    print("=" * 40)
    
    # Create test database
    db_manager = DatabaseManager("test_meal_planner.db")
    
    try:
        # Initialize database
        print("📋 Initializing database...")
        db_manager.initialize_database()
        print("✅ Database initialized successfully")
        
        # Check applied migrations
        migrations = db_manager.get_applied_migrations()
        print(f"📦 Applied migrations: {migrations}")
        
        # Test database connection
        print("🔗 Testing database connection...")
        with db_manager.get_connection() as conn:
            # Test basic query
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            print(f"📊 Created tables: {tables}")
            
            # Test foreign key constraints
            cursor = conn.execute("PRAGMA foreign_keys")
            fk_enabled = cursor.fetchone()[0]
            print(f"🔐 Foreign keys enabled: {bool(fk_enabled)}")
            
        print("✅ Database test completed successfully!")
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False
    
    finally:
        # Clean up test database
        if os.path.exists("test_meal_planner.db"):
            os.remove("test_meal_planner.db")
            print("🧹 Test database cleaned up")
    
    return True

def test_id_generation():
    """Test ID generation utility."""
    print("\n🆔 Testing ID Generation")
    print("=" * 25)
    
    db_manager = DatabaseManager()
    
    # Generate test IDs
    ids = [db_manager.generate_id() for _ in range(3)]
    print(f"Generated IDs: {ids}")
    
    # Verify uniqueness
    assert len(set(ids)) == len(ids), "IDs should be unique"
    print("✅ ID generation test passed")

if __name__ == "__main__":
    print("🧪 Database Schema & Migration Test Suite")
    print("=" * 50)
    
    success = True
    
    # Run tests
    success &= test_database_initialization()
    test_id_generation()
    
    if success:
        print("\n🎉 All database tests passed!")
        print("Ready for Task 2.1: User Management Repository")
    else:
        print("\n❌ Some tests failed. Check the errors above.")
        sys.exit(1)
