"""
Settings view: low-frequency household + personal admin in one place.

Two tabs:
- **Profile** — body composition + daily calorie target.
- **Household** — invite code (with copy button) + member list.

Splitting these as separate sidebar items felt heavy; users open them
rarely. Tucking them under one Settings page keeps the primary nav
short and task-shaped (Today / Plan / Recipes / etc.).
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

import streamlit as st

from core.interfaces.user_repository import IUserRepository, UserProfile
from core.services.flexible_dieting import BodyCompositionService
from repositories.sqlite.household_repository import SQLiteHouseholdRepository
from repositories.sqlite.user_repository import SQLiteUserRepository


_ACTIVITY_LEVELS = ["sedentary", "light", "moderate", "active", "very_active"]
_ACTIVITY_LABELS = {
    "sedentary": "Sedentary (little/no exercise)",
    "light": "Light (1–3 days/wk)",
    "moderate": "Moderate (3–5 days/wk)",
    "active": "Active (6–7 days/wk)",
    "very_active": "Very active (intense, daily)",
}


def render(user: UserProfile,
           user_repo: IUserRepository,
           body_comp: BodyCompositionService,
           household_repo: SQLiteHouseholdRepository,
           sqlite_user_repo: SQLiteUserRepository) -> None:
    st.title("Settings")
    st.caption("Your profile, your calorie goal, and your household.")
    tab_profile, tab_household = st.tabs(["Profile", "Household"])
    with tab_profile:
        _render_profile(user, user_repo, body_comp)
    with tab_household:
        _render_household(user, household_repo, sqlite_user_repo)


# --------------------------------------------------------------- Profile tab

def _render_profile(user: UserProfile,
                    user_repo: IUserRepository,
                    body_comp: BodyCompositionService) -> None:
    st.subheader("Daily calorie goal")
    if user.daily_calorie_target:
        st.write(f"Your current goal: **{user.daily_calorie_target} cal/day**.")
    else:
        st.caption(
            "No goal set yet. Either compute one from your body composition "
            "below, or set a number directly under 'Set manually'."
        )

    st.markdown("**Compute from body composition**")
    with st.form("body_comp_form"):
        weight_str = st.text_input(
            "Weight (lb)",
            value=str(user.current_weight) if user.current_weight is not None else "",
        ).strip()
        bf_str = st.text_input(
            "Body fat (%)",
            value=str(user.body_fat_percentage) if user.body_fat_percentage is not None else "",
        ).strip()
        activity = st.selectbox(
            "Activity level",
            _ACTIVITY_LEVELS,
            index=_ACTIVITY_LEVELS.index("moderate"),
            format_func=lambda key: _ACTIVITY_LABELS[key],
        )
        compute = st.form_submit_button("Compute target")

    if compute:
        weight = _parse_decimal(weight_str, "Weight")
        bf = _parse_decimal(bf_str, "Body fat")
        if weight is None or bf is None:
            return
        assessment = body_comp.assess_body_composition(
            body_fat_percentage=bf,
            current_weight=weight,
            activity_level=activity,
        )
        st.session_state.profile_assessment = {
            "weight": weight,
            "body_fat": bf,
            "daily_target": assessment.daily_calorie_target,
            "weekly_target": assessment.weekly_calorie_target,
            "category": assessment.assessment_category,
            "recommended_loss": assessment.recommended_weight_loss_per_week,
        }

    assessment = st.session_state.get("profile_assessment")
    if assessment:
        st.success(
            f"**{assessment['daily_target']} cal/day** "
            f"(category: {assessment['category']}, "
            f"recommended loss: {assessment['recommended_loss']}%/wk)"
        )
        if st.button("Save this as my daily target", type="primary"):
            updated = UserProfile(
                user_id=user.user_id,
                name=user.name,
                email=user.email,
                current_weight=assessment["weight"],
                body_fat_percentage=assessment["body_fat"],
                target_weight_loss_per_week=assessment["recommended_loss"],
                daily_calorie_target=assessment["daily_target"],
                household_id=user.household_id,
                is_planner=user.is_planner,
                password_hash=user.password_hash,
            )
            user_repo.update_profile(updated)
            st.session_state.user = updated
            del st.session_state.profile_assessment
            st.toast("Goal saved. Today's page will use it.", icon=":material/check_circle:")
            st.rerun()

    with st.expander("Set manually"):
        with st.form("manual_target"):
            manual = st.number_input(
                "Daily calorie target",
                min_value=800, max_value=6000,
                value=user.daily_calorie_target or 2000,
                step=50,
            )
            save_manual = st.form_submit_button("Save target")
        if save_manual:
            updated = UserProfile(
                user_id=user.user_id,
                name=user.name,
                email=user.email,
                current_weight=user.current_weight,
                body_fat_percentage=user.body_fat_percentage,
                target_weight_loss_per_week=user.target_weight_loss_per_week,
                daily_calorie_target=int(manual),
                household_id=user.household_id,
                is_planner=user.is_planner,
                password_hash=user.password_hash,
            )
            user_repo.update_profile(updated)
            st.session_state.user = updated
            st.toast(f"Saved {int(manual)} cal/day.", icon=":material/check_circle:")
            st.rerun()


# ------------------------------------------------------------- Household tab

def _render_household(user: UserProfile,
                      household_repo: SQLiteHouseholdRepository,
                      user_repo: SQLiteUserRepository) -> None:
    if not user.household_id:
        st.warning("You're not in a household yet.")
        return
    household = household_repo.find_by_id(user.household_id)
    if household is None:
        st.error("Household not found. Please log out and back in.")
        return

    st.subheader(household.name)

    st.markdown("**Invite code**")
    st.caption(
        "Anyone you share this code with can join your household by entering "
        "it on the 'Join a household' screen. Treat it like a password — "
        "anyone who has it can become a member."
    )
    # Single-line text input + copy widget: more tap-friendly on mobile
    # than a code block that requires a long-press menu to copy from.
    st.text_input(
        "Code",
        value=household.id,
        key=f"invite_code_{household.id}",
        label_visibility="collapsed",
        disabled=True,
        help="Tap the copy icon at the right of the box.",
    )

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
    profiles.sort(key=lambda p: (not p.is_planner, p.name.lower()))
    for profile in profiles:
        role = "Planner" if profile.is_planner else "Member"
        you_chip = " (you)" if profile.user_id == user.user_id else ""
        st.write(f"- **{profile.name}**{you_chip} — _{role}_")


def _parse_decimal(raw: str, label: str):
    if not raw:
        st.error(f"{label} is required.")
        return None
    try:
        return Decimal(raw)
    except InvalidOperation:
        st.error(f"{label} '{raw}' isn't a number.")
        return None
