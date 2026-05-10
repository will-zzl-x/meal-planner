"""
Household page: shows the household's invite code and member list.

The invite code is the household's UUID — anyone the planner shares it
with can use it on the "Join a household" tab to register a member
account that's automatically scoped to this household. UUIDs aren't
the prettiest invite codes (they're long), but they're cryptographically
unguessable, which matters because the code is the only access control
on the join flow.
"""
from __future__ import annotations

import streamlit as st

from core.interfaces.user_repository import UserProfile
from repositories.sqlite.household_repository import SQLiteHouseholdRepository
from repositories.sqlite.user_repository import SQLiteUserRepository


def render(user: UserProfile,
           household_repo: SQLiteHouseholdRepository,
           user_repo: SQLiteUserRepository) -> None:
    st.title("Household")

    if not user.household_id:
        st.warning("You're not in a household yet.")
        return

    household = household_repo.find_by_id(user.household_id)
    if household is None:
        st.error("Household not found. (This shouldn't happen — please log out and back in.)")
        return

    st.subheader(household.name)

    st.markdown("**Invite code**")
    st.caption(
        "Anyone you share this code with can join your household by entering "
        "it on the 'Join a household' screen. Treat it like a password — "
        "anyone who has it can become a member."
    )
    st.code(household.id, language=None)

    st.divider()
    _render_members(user, household_repo, user_repo)


def _render_members(user: UserProfile,
                    household_repo: SQLiteHouseholdRepository,
                    user_repo: SQLiteUserRepository) -> None:
    st.markdown("**Members**")
    member_ids = household_repo.list_member_ids(user.household_id)
    if not member_ids:
        st.caption("No members yet — that's odd, you should be in here.")
        return

    profiles = [user_repo.find_by_id(mid) for mid in member_ids]
    profiles = [p for p in profiles if p is not None]
    # Planner first, then alphabetical by name.
    profiles.sort(key=lambda p: (not p.is_planner, p.name.lower()))

    for profile in profiles:
        role = "Planner" if profile.is_planner else "Member"
        you_chip = " (you)" if profile.user_id == user.user_id else ""
        st.write(f"- **{profile.name}**{you_chip} — _{role}_")
