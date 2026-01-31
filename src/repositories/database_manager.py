"""
Database initialization and migration utilities.
Based on patterns from successful open source nutrition apps.
"""
import sqlite3
import os
from pathlib import Path
from typing import Optional
import uuid
from datetime import datetime

class DatabaseManager:
    """Manages SQLite database initialization and migrations."""
    
    def __init__(self, db_path: str = "meal_planner.db"):
        self.db_path = db_path
        self.schema_path = Path(__file__).parent / "schema.sql"
    
    def initialize_database(self) -> bool:
        """
        Initialize the database with schema.
        Returns True if successful, False otherwise.
        """
        try:
            # Create database directory if it doesn't exist
            os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True)
            
            # Read schema file
            with open(self.schema_path, 'r') as f:
                schema_sql = f.read()
            
            # Execute schema
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(schema_sql)
                conn.commit()
            
            print(f"✅ Database initialized successfully at {self.db_path}")
            return True
            
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            return False
    
    def create_sample_data(self) -> bool:
        """
        Create sample data for testing (based on open source app patterns).
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Sample ingredients (common nutrition app ingredients)
                sample_ingredients = [
                    ("Chicken Breast", 165, 31.0, 0.0, 3.6),
                    ("Bell Pepper", 31, 1.0, 7.0, 0.3),
                    ("Yellow Onion", 40, 1.1, 9.3, 0.1),
                    ("Garlic", 149, 6.4, 33.1, 0.5),
                    ("Olive Oil", 884, 0.0, 0.0, 100.0),
                    ("White Rice", 130, 2.7, 28.0, 0.3),
                    ("Broccoli", 34, 2.8, 7.0, 0.4),
                    ("Salmon Fillet", 208, 25.4, 0.0, 12.4)
                ]
                
                for ingredient_data in sample_ingredients:
                    ingredient_id = str(uuid.uuid4())
                    cursor.execute("""
                        INSERT OR IGNORE INTO ingredients 
                        (id, name, calories_per_100g, protein_per_100g, carbs_per_100g, fat_per_100g)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (ingredient_id, *ingredient_data))
                
                # Sample store profile
                store_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT OR IGNORE INTO store_profiles (id, name)
                    VALUES (?, ?)
                """, (store_id, "Generic Store"))
                
                conn.commit()
                print("✅ Sample data created successfully")
                return True
                
        except Exception as e:
            print(f"❌ Sample data creation failed: {e}")
            return False
    
    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection with proper configuration."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
        return conn
    
    def check_database_exists(self) -> bool:
        """Check if database file exists and has tables."""
        if not os.path.exists(self.db_path):
            return False
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
                return cursor.fetchone() is not None
        except:
            return False
    
    def get_database_info(self) -> dict:
        """Get information about the database."""
        if not self.check_database_exists():
            return {"exists": False}
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get table count
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count = cursor.fetchone()[0]
                
                # Get user count
                cursor.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()[0]
                
                # Get recipe count
                cursor.execute("SELECT COUNT(*) FROM recipes")
                recipe_count = cursor.fetchone()[0]
                
                # Get ingredient count
                cursor.execute("SELECT COUNT(*) FROM ingredients")
                ingredient_count = cursor.fetchone()[0]
                
                return {
                    "exists": True,
                    "path": self.db_path,
                    "tables": table_count,
                    "users": user_count,
                    "recipes": recipe_count,
                    "ingredients": ingredient_count
                }
        except Exception as e:
            return {"exists": True, "error": str(e)}

def main():
    """CLI interface for database management."""
    import sys
    
    db_manager = DatabaseManager()
    
    if len(sys.argv) < 2:
        print("Usage: python database_manager.py [init|info|sample]")
        return
    
    command = sys.argv[1]
    
    if command == "init":
        success = db_manager.initialize_database()
        if success:
            db_manager.create_sample_data()
    
    elif command == "info":
        info = db_manager.get_database_info()
        print("📊 Database Information:")
        for key, value in info.items():
            print(f"  {key}: {value}")
    
    elif command == "sample":
        db_manager.create_sample_data()
    
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
