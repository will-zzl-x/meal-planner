"""
Authentication service for V1 multi-account households.

Wires password hashing to the user/household repositories. The Streamlit UI
calls into this layer for register/login flows; the repositories never see
plaintext passwords.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from typing import TYPE_CHECKING

from core.interfaces.household_repository import Household, IHouseholdRepository
from core.interfaces.recipe_repository import IRecipeRepository
from core.interfaces.user_repository import IUserRepository, UserProfile
from core.services.password_hashing import (
    DEFAULT_ITERATIONS,
    hash_password,
    verify_password,
)
from core.seed_recipes import seed_recipes_for_household

if TYPE_CHECKING:
    # Type-only — avoids a hard runtime dependency on the backfiller
    # (and its repo concretes) when AuthService is used in test fixtures
    # that don't need backfill behavior.
    from core.services.seed_recipe_backfiller import SeedRecipeBackfiller


class AuthError(Exception):
    """Base class for authentication errors raised by AuthService."""


class EmailAlreadyRegisteredError(AuthError):
    """Raised when registering an email address that already has an account."""


class HouseholdNotFoundError(AuthError):
    """Raised when joining a household with an unknown household ID."""


@dataclass
class HouseholdRegistration:
    """Result of registering a brand-new household. Returns both the planner's
    profile and the freshly created household so the caller can show the
    invite-code (= household.id) without an extra lookup."""
    user: UserProfile
    household: Household


class AuthService:
    """Register and log in users for the household-based meal planner."""

    def __init__(self,
                 user_repo: IUserRepository,
                 household_repo: IHouseholdRepository,
                 *,
                 recipe_repo: Optional[IRecipeRepository] = None,
                 backfiller: Optional["SeedRecipeBackfiller"] = None,
                 hash_iterations: int = DEFAULT_ITERATIONS):
        self.user_repo = user_repo
        self.household_repo = household_repo
        self.recipe_repo = recipe_repo  # When set, register_household seeds starter recipes.
        # When set alongside recipe_repo, the seeded recipes are auto-
        # backfilled with real catalog references right after seeding so
        # the new household sees real calorie numbers immediately. The
        # backfill is best-effort — anything it can't match stays as
        # legacy free-text and the planner can fix via the picker.
        self.backfiller = backfiller
        self._hash_iterations = hash_iterations

    def register_household(self,
                           planner_name: str,
                           email: str,
                           password: str,
                           household_name: str) -> HouseholdRegistration:
        """Create a new household and register the planner as its first user.

        If a recipe repo was supplied at construction, the new household is
        automatically seeded with the built-in starter recipes.
        """
        self._reject_if_email_in_use(email)
        household = self.household_repo.create(household_name)
        user = self.user_repo.create_user(
            name=planner_name,
            email=email,
            password_hash=self._hash(password),
            household_id=household.id,
            is_planner=True,
        )
        if self.recipe_repo is not None:
            seed_recipes_for_household(self.recipe_repo, household.id, user.user_id)
            if self.backfiller is not None:
                # Best-effort: failures in the backfiller (network, etc.)
                # must not block household registration. The user can always
                # rerun the backfill from the CLI later.
                try:
                    self.backfiller.backfill_household(household.id)
                except Exception:
                    pass
        return HouseholdRegistration(user=user, household=household)

    def register_member(self,
                        name: str,
                        email: str,
                        password: str,
                        household_id: str) -> UserProfile:
        """Add a non-planner user to an existing household."""
        if self.household_repo.find_by_id(household_id) is None:
            raise HouseholdNotFoundError(household_id)
        self._reject_if_email_in_use(email)
        return self.user_repo.create_user(
            name=name,
            email=email,
            password_hash=self._hash(password),
            household_id=household_id,
            is_planner=False,
        )

    def login(self, email: str, password: str) -> Optional[UserProfile]:
        """Return the user profile on correct credentials, None otherwise."""
        user = self.user_repo.find_by_email(email)
        if user is None or user.password_hash is None:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def _hash(self, password: str) -> str:
        return hash_password(password, iterations=self._hash_iterations)

    def _reject_if_email_in_use(self, email: str) -> None:
        if self.user_repo.find_by_email(email) is not None:
            raise EmailAlreadyRegisteredError(email)
