"""
User repository interface for user management operations.
"""
from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class UserProfile:
    """User profile with body composition, calorie targets, and household auth fields."""
    user_id: str
    name: str
    email: Optional[str]
    current_weight: Optional[Decimal]
    body_fat_percentage: Optional[Decimal]
    target_weight_loss_per_week: Optional[Decimal]
    daily_calorie_target: Optional[int]
    household_id: Optional[str] = None
    is_planner: bool = False
    password_hash: Optional[str] = None  # Stored hash; None for unregistered/legacy users.


class IUserRepository(ABC):
    """Interface for user data access operations."""

    @abstractmethod
    def create_user(self,
                    name: str,
                    email: Optional[str] = None,
                    password_hash: Optional[str] = None,
                    household_id: Optional[str] = None,
                    is_planner: bool = False) -> UserProfile:
        """Create a new user. The password is expected pre-hashed by the caller."""
        pass

    @abstractmethod
    def find_by_id(self, user_id: str) -> Optional[UserProfile]:
        """Find user by ID."""
        pass

    @abstractmethod
    def find_by_email(self, email: str) -> Optional[UserProfile]:
        """Find user by email address (used by the login flow)."""
        pass

    @abstractmethod
    def update_profile(self, user_profile: UserProfile) -> UserProfile:
        """Update user profile information (does NOT change password_hash)."""
        pass

    @abstractmethod
    def update_password_hash(self, user_id: str, password_hash: str) -> bool:
        """Replace the stored password hash for an existing user."""
        pass

    @abstractmethod
    def delete_user(self, user_id: str) -> bool:
        """Delete a user and all associated data."""
        pass
