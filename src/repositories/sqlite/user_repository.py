"""
SQLite implementation of User Repository.
Based on patterns from successful open source nutrition apps.
"""
import sqlite3
import uuid
from typing import Optional
from datetime import datetime
from decimal import Decimal

from ..core.interfaces.user_repository import IUserRepository, UserProfile
from ..database_manager import DatabaseManager

class SQLiteUserRepository(IUserRepository):
    """SQLite implementation of user data access."""
    
    def __init__(self, db_path: str = "meal_planner.db"):
        self.db_manager = DatabaseManager(db_path)
        
        # Initialize database if it doesn't exist
        if not self.db_manager.check_database_exists():
            self.db_manager.initialize_database()
    
    def create_user(self, name: str, email: Optional[str] = None) -> UserProfile:
        """Create a new user with profile."""
        user_id = str(uuid.uuid4())
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create user
            cursor.execute("""
                INSERT INTO users (id, name, email)
                VALUES (?, ?, ?)
            """, (user_id, name, email))
            
            # Create empty profile
            cursor.execute("""
                INSERT INTO user_profiles (user_id)
                VALUES (?)
            """, (user_id,))
            
            conn.commit()
        
        return UserProfile(
            user_id=user_id,
            name=name,
            email=email,
            current_weight=None,
            body_fat_percentage=None,
            target_weight_loss_per_week=None,
            daily_calorie_target=None
        )
    
    def find_by_id(self, user_id: str) -> Optional[UserProfile]:
        """Find user by ID with profile data."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT u.id, u.name, u.email,
                       p.current_weight, p.body_fat_percentage,
                       p.target_weight_loss_per_week, p.daily_calorie_target
                FROM users u
                LEFT JOIN user_profiles p ON u.id = p.user_id
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
    
    def find_by_email(self, email: str) -> Optional[UserProfile]:
        """Find user by email address."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT u.id, u.name, u.email,
                       p.current_weight, p.body_fat_percentage,
                       p.target_weight_loss_per_week, p.daily_calorie_target
                FROM users u
                LEFT JOIN user_profiles p ON u.id = p.user_id
                WHERE u.email = ?
            """, (email,))
            
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
        """Update user profile information."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Update user basic info
            cursor.execute("""
                UPDATE users 
                SET name = ?, email = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (user_profile.name, user_profile.email, user_profile.user_id))
            
            # Update profile data
            cursor.execute("""
                UPDATE user_profiles 
                SET current_weight = ?, 
                    body_fat_percentage = ?,
                    target_weight_loss_per_week = ?,
                    daily_calorie_target = ?,
                    updated_at = CURRENT_TIMESTAMP
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
    
    def delete_user(self, user_id: str) -> bool:
        """Delete a user and all associated data."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
            if not cursor.fetchone():
                return False
            
            # Delete user (CASCADE will handle related data)
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            
            return cursor.rowcount > 0
