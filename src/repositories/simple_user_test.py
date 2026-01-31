#!/usr/bin/env python3
"""
Simple test for User Repository - inline implementation.
"""
import sqlite3
import uuid
from decimal import Decimal
from typing import Optional
from dataclasses import dataclass

@dataclass
class UserProfile:
    """User profile with body composition and calorie targets."""
    user_id: str
    name: str
    email: Optional[str]
    current_weight: Optional[Decimal]
    body_fat_percentage: Optional[Decimal]
    target_weight_loss_per_week: Optional[Decimal]
    daily_calorie_target: Optional[int]

class SimpleUserRepository:
    """Simple SQLite user repository for testing."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database with minimal schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    current_weight DECIMAL(5,2),
                    body_fat_percentage DECIMAL(4,2),
                    target_weight_loss_per_week DECIMAL(3,2),
                    daily_calorie_target INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """)
    
    def create_user(self, name: str, email: Optional[str] = None) -> UserProfile:
        """Create a new user."""
        user_id = str(uuid.uuid4())
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("INSERT INTO users (id, name, email) VALUES (?, ?, ?)", 
                         (user_id, name, email))
            cursor.execute("INSERT INTO user_profiles (user_id) VALUES (?)", (user_id,))
            conn.commit()
        
        return UserProfile(user_id, name, email, None, None, None, None)
    
    def find_by_id(self, user_id: str) -> Optional[UserProfile]:
        """Find user by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT u.id, u.name, u.email, p.current_weight, p.body_fat_percentage,
                       p.target_weight_loss_per_week, p.daily_calorie_target
                FROM users u LEFT JOIN user_profiles p ON u.id = p.user_id
                WHERE u.id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return UserProfile(
                user_id=row['id'],
                name=row['name'],
                email=row['email'],
                current_weight=Decimal(str(row['current_weight'])) if row['current_weight'] else None,
                body_fat_percentage=Decimal(str(row['body_fat_percentage'])) if row['body_fat_percentage'] else None,
                target_weight_loss_per_week=Decimal(str(row['target_weight_loss_per_week'])) if row['target_weight_loss_per_week'] else None,
                daily_calorie_target=row['daily_calorie_target']
            )
    
    def update_profile(self, user_profile: UserProfile) -> UserProfile:
        """Update user profile."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("UPDATE users SET name = ?, email = ? WHERE id = ?",
                         (user_profile.name, user_profile.email, user_profile.user_id))
            
            cursor.execute("""
                UPDATE user_profiles 
                SET current_weight = ?, body_fat_percentage = ?, 
                    target_weight_loss_per_week = ?, daily_calorie_target = ?
                WHERE user_id = ?
            """, (
                float(user_profile.current_weight) if user_profile.current_weight else None,
                float(user_profile.body_fat_percentage) if user_profile.body_fat_percentage else None,
                float(user_profile.target_weight_loss_per_week) if user_profile.target_weight_loss_per_week else None,
                user_profile.daily_calorie_target,
                user_profile.user_id
            ))
            
            conn.commit()
        
        return user_profile

def test_user_repository():
    """Test user repository operations."""
    print("🧪 Testing User Repository")
    print("=" * 30)
    
    repo = SimpleUserRepository("test_users.db")
    
    # Test 1: Create user
    print("1. Creating user...")
    user = repo.create_user("John Doe", "john@example.com")
    print(f"   ✅ Created: {user.name} (ID: {user.user_id[:8]}...)")
    
    # Test 2: Find user
    print("2. Finding user...")
    found = repo.find_by_id(user.user_id)
    if found and found.name == "John Doe":
        print(f"   ✅ Found: {found.name}")
    else:
        print("   ❌ Not found")
        return
    
    # Test 3: Update profile
    print("3. Updating profile...")
    user.current_weight = Decimal("180.5")
    user.body_fat_percentage = Decimal("15.0")
    user.daily_calorie_target = 2000
    
    updated = repo.update_profile(user)
    print(f"   ✅ Updated: {updated.current_weight} lbs, {updated.body_fat_percentage}% BF, {updated.daily_calorie_target} cal")
    
    # Test 4: Verify persistence
    print("4. Verifying persistence...")
    reloaded = repo.find_by_id(user.user_id)
    if reloaded and reloaded.current_weight == Decimal("180.5"):
        print(f"   ✅ Persisted: {reloaded.current_weight} lbs")
    else:
        print("   ❌ Not persisted")
        return
    
    print("\n🎉 All tests passed! User Repository working correctly.")
    
    # Cleanup
    import os
    os.remove("test_users.db")
    print("🧹 Test database cleaned up.")

if __name__ == "__main__":
    test_user_repository()
