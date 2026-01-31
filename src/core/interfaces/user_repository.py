"""
User repository interface for user management operations.
"""
from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass
from decimal import Decimal

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

class IUserRepository(ABC):
    """Interface for user data access operations."""
    
    @abstractmethod
    def create_user(self, name: str, email: Optional[str] = None) -> UserProfile:
        """
        Create a new user.
        
        Args:
            name: User's name
            email: Optional email address
            
        Returns:
            Created user profile with generated ID
        """
        pass
    
    @abstractmethod
    def find_by_id(self, user_id: str) -> Optional[UserProfile]:
        """
        Find user by ID.
        
        Args:
            user_id: ID of the user
            
        Returns:
            User profile if found, None otherwise
        """
        pass
    
    @abstractmethod
    def find_by_email(self, email: str) -> Optional[UserProfile]:
        """
        Find user by email address.
        
        Args:
            email: Email address
            
        Returns:
            User profile if found, None otherwise
        """
        pass
    
    @abstractmethod
    def update_profile(self, user_profile: UserProfile) -> UserProfile:
        """
        Update user profile information.
        
        Args:
            user_profile: Updated user profile
            
        Returns:
            Updated user profile
        """
        pass
    
    @abstractmethod
    def delete_user(self, user_id: str) -> bool:
        """
        Delete a user and all associated data.
        
        Args:
            user_id: ID of the user to delete
            
        Returns:
            True if deleted, False if not found
        """
        pass
