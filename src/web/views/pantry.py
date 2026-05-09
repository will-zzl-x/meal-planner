"""
Pantry page: list household pantry items; planner can add and remove.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

import streamlit as st

from core.domain.models import InventoryItem
from core.domain.security import SecurityValidationError
from core.interfaces.user_repository import UserProfile
from repositories.sqlite.inventory_repository import SQLiteInventoryRepository


# Common pantry unit options (selectbox order). The unit validator is now
# permissive, so anything alphanumeric works — these are just the easy picks.
_UNIT_OPTIONS = ["oz", "lb", "cup", "tbsp", "tsp", "cloves",
                 "small", "medium", "large", "scoop", "whole"]


def render(user: UserProfile, repo: SQLiteInventoryRepository) -> None:
    st.title("Pantry")
    st.caption(f"Items shared across your household. {'You can add and remove.' if user.is_planner else 'Only the planner can add or remove.'}")

    if not user.household_id:
        st.warning("You're not in a household yet. Ask the planner for an invite code.")
        return

    _render_pantry_list(user, repo)
    if user.is_planner:
        st.divider()
        _render_add_item_form(user, repo)


def _render_pantry_list(user: UserProfile, repo: SQLiteInventoryRepository) -> None:
    items = repo.get_household_inventory(user.household_id)
    if not items:
        st.info("Pantry is empty. " + ("Add your first item below!" if user.is_planner else "Ask the planner to add some."))
        return

    for item in items:
        col_label, col_action = st.columns([4, 1])
        col_label.write(f"**{item.name}** — {item.quantity} {item.unit}")
        if user.is_planner:
            if col_action.button("Remove", key=f"remove-{item.name}-{item.unit}", type="secondary"):
                repo.remove_inventory_item(user.household_id, item.name, item.unit)
                st.rerun()


def _render_add_item_form(user: UserProfile, repo: SQLiteInventoryRepository) -> None:
    st.subheader("Add an item")
    st.caption("Adding the same name and unit again replaces the quantity.")
    with st.form("add_pantry_item", clear_on_submit=True):
        col_name, col_qty, col_unit = st.columns([3, 1, 1])
        with col_name:
            name = st.text_input("Item").strip()
        with col_qty:
            qty_str = st.text_input("Qty", value="1")
        with col_unit:
            unit = st.selectbox("Unit", _UNIT_OPTIONS, index=0)
        submit = st.form_submit_button("Add to pantry")

    if not submit:
        return
    if not name:
        st.error("Item name is required.")
        return
    try:
        qty = Decimal(qty_str)
    except InvalidOperation:
        st.error(f"Quantity '{qty_str}' isn't a number.")
        return
    try:
        item = InventoryItem(name=name, quantity=qty, unit=unit)
        repo.add_inventory_item(user.household_id, item)
    except SecurityValidationError as e:
        st.error(f"Invalid input: {e}")
        return

    st.success(f"Added '{name}' to pantry.")
    st.rerun()
