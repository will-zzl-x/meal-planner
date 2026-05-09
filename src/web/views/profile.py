"""
My Profile view: weight + body fat + activity → daily calorie target.

Uses BodyCompositionService.assess_body_composition (Katch-McArdle BMR scaled
by activity, deficit derived from body-fat category) to suggest a target.
The user can save the suggestion or override it manually.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

import streamlit as st

from core.interfaces.user_repository import IUserRepository, UserProfile
from core.services.flexible_dieting import BodyCompositionService


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
           body_comp: BodyCompositionService) -> None:
    st.title("My Profile")

    st.subheader("Body composition")
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
        if st.button("Save this as my daily target"):
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
            st.success("Saved. Today's page will use the new target.")
            st.rerun()

    st.divider()
    st.subheader("Current daily target")
    if user.daily_calorie_target:
        st.write(f"**{user.daily_calorie_target} cal/day**")
    else:
        st.caption("Not set yet. Use the form above to compute and save one.")

    with st.expander("Set a target manually"):
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
            st.success(f"Saved daily target of {int(manual)} cal.")
            st.rerun()


def _parse_decimal(raw: str, label: str):
    if not raw:
        st.error(f"{label} is required.")
        return None
    try:
        return Decimal(raw)
    except InvalidOperation:
        st.error(f"{label} '{raw}' isn't a number.")
        return None
