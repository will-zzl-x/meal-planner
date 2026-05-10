"""
Pantry page: list household pantry items; planner can add and remove.

Pantry items can optionally link to the same food-database catalog rows
recipe ingredients use, so coverage matching ("do I have everything for
this recipe?") can compare by exact catalog reference rather than by
fuzzy free-text name. The link is created via a small "Link to a food
database entry" expander above the existing add form. Quantity and unit
stay in natural shopping units (lb, cup, oz, etc.) — the catalog ref is
metadata for matching, not the user's display unit.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

import streamlit as st

from core.domain.models import InventoryItem
from core.domain.security import SecurityValidationError
from core.interfaces.user_repository import UserProfile
from core.services.food_database_service import FoodDatabaseService
from repositories.sqlite.ingredient_catalog_repository import (
    SQLiteIngredientCatalogRepository,
)
from repositories.sqlite.inventory_repository import SQLiteInventoryRepository


# Common pantry unit options (selectbox order). The unit validator is now
# permissive, so anything alphanumeric works — these are just the easy picks.
_UNIT_OPTIONS = ["oz", "lb", "cup", "tbsp", "tsp", "g", "kg", "cloves",
                 "small", "medium", "large", "scoop", "whole"]

# Session-state keys the search-link flow uses. Per-household so they
# don't bleed across logins on the same machine.
_LINKED_NAME_KEY = "pantry_linked_name"
_LINKED_CATALOG_ID_KEY = "pantry_linked_catalog_id"
_SEARCH_RESULTS_KEY = "pantry_search_results"
_LAST_QUERY_KEY = "pantry_last_query"


def render(user: UserProfile,
           repo: SQLiteInventoryRepository,
           food_db: FoodDatabaseService,
           catalog_repo: SQLiteIngredientCatalogRepository) -> None:
    st.title("Pantry")
    st.caption(
        f"Items shared across your household. "
        f"{'You can add and remove.' if user.is_planner else 'Only the planner can add or remove.'}"
    )

    if not user.household_id:
        st.warning("You're not in a household yet. Ask the planner for an invite code.")
        return

    _render_pantry_list(user, repo)
    if user.is_planner:
        st.divider()
        _render_add_item_form(user, repo, food_db, catalog_repo)


def _render_pantry_list(user: UserProfile, repo: SQLiteInventoryRepository) -> None:
    items = repo.get_household_inventory(user.household_id)
    if not items:
        st.info(
            "Pantry is empty. "
            + ("Add your first item below!" if user.is_planner else "Ask the planner to add some.")
        )
        return

    for item in items:
        # Wider Remove column ([4,2]) for finger-friendly tap area.
        col_label, col_action = st.columns([4, 2])
        link_chip = " 🔗" if item.catalog_ingredient_id else ""
        col_label.write(f"**{item.name}**{link_chip} — {item.quantity} {item.unit}")
        if user.is_planner:
            if col_action.button("Remove", key=f"remove-{item.name}-{item.unit}",
                                 type="secondary", use_container_width=True):
                repo.remove_inventory_item(user.household_id, item.name, item.unit)
                st.rerun()


# ----------------------------------------------------------------- add form

def _render_add_item_form(user: UserProfile,
                          repo: SQLiteInventoryRepository,
                          food_db: FoodDatabaseService,
                          catalog_repo: SQLiteIngredientCatalogRepository) -> None:
    st.subheader("Add an item")
    st.caption("Adding the same name and unit again replaces the quantity.")

    _render_link_search(food_db, catalog_repo)

    linked_name = st.session_state.get(_LINKED_NAME_KEY)
    linked_catalog_id: Optional[str] = st.session_state.get(_LINKED_CATALOG_ID_KEY)

    if linked_name and linked_catalog_id:
        cols = st.columns([5, 2])
        cols[0].markdown(f"🔗 **Linked to:** {linked_name}")
        if cols[1].button("Clear link", key="pantry_clear_link",
                          use_container_width=True):
            _clear_link_stash()
            st.rerun()

    # clear_on_submit=False so the user doesn't lose their typed values
    # when validation fails (bad qty, name with disallowed chars, etc.).
    # On success we explicitly pop the input keys before rerun.
    with st.form("add_pantry_item", clear_on_submit=False):
        col_name, col_qty, col_unit = st.columns([3, 1, 1])
        with col_name:
            # If the user picked a catalog item, pre-fill the name with
            # its display name. The session-state key holds the value so
            # Streamlit won't override the pre-fill on subsequent renders.
            if linked_name and not st.session_state.get("pantry_name"):
                st.session_state["pantry_name"] = linked_name
            name = st.text_input("Item", key="pantry_name").strip()
        with col_qty:
            qty_str = st.text_input("Qty", value="1", key="pantry_qty")
        with col_unit:
            unit = st.selectbox("Unit", _UNIT_OPTIONS, index=0, key="pantry_unit")
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
        item = InventoryItem(
            name=name, quantity=qty, unit=unit,
            catalog_ingredient_id=linked_catalog_id,
        )
        repo.add_inventory_item(user.household_id, item)
    except SecurityValidationError as e:
        st.error(f"Invalid input: {e}")
        return

    # Reset the inputs and the catalog stash only after a successful save.
    st.session_state.pop("pantry_name", None)
    st.session_state.pop("pantry_qty", None)
    _clear_link_stash()
    st.success(f"Added '{name}' to pantry.")
    st.rerun()


# -------------------------------------------------------- search-link flow

def _render_link_search(food_db: FoodDatabaseService,
                        catalog_repo: SQLiteIngredientCatalogRepository) -> None:
    """Small search widget that lets the user pick a catalog item to link
    the next pantry add to. Runs as a sibling block above the regular
    add form. Picking a result stages it in session state; the regular
    form's submit handler reads it on save.

    Why not reuse render_food_picker? The picker's flow is "pick →
    immediately commit with a servings count". Pantry needs "pick → user
    fills in qty + unit in a separate form → commit". So a small
    custom flow is the smaller change.
    """
    with st.expander("Link to a food database entry (optional, recommended)"):
        st.caption(
            "Links this pantry item to a USDA / Open Food Facts entry so "
            "the recipe pages know what you have. You still type your "
            "quantity and unit (e.g. '2 lb', '5 cups') in the form below."
        )

        with st.form("pantry_link_search_form", clear_on_submit=False):
            query = st.text_input(
                "Search foods", key="pantry_link_query",
                placeholder="e.g. white rice, chicken breast",
            )
            searched = st.form_submit_button("Search")

        if searched and query.strip():
            with st.spinner("Searching food databases…"):
                st.session_state[_SEARCH_RESULTS_KEY] = food_db.search_food_database(
                    query.strip(), limit=12,
                )
            st.session_state[_LAST_QUERY_KEY] = query.strip()

        results = st.session_state.get(_SEARCH_RESULTS_KEY) or []
        last_query = st.session_state.get(_LAST_QUERY_KEY)

        if last_query and not results:
            st.caption(
                f"No matches for '{last_query}'. Try a simpler query, or "
                "skip the link and just type a name in the form below."
            )
            return
        if not results:
            return

        st.caption(f"{len(results)} result(s). Pick one to link this pantry item to it.")
        for idx, item in enumerate(results):
            _render_pick_row(item, idx, catalog_repo)


def _render_pick_row(item, idx: int, catalog_repo: SQLiteIngredientCatalogRepository) -> None:
    name_line = f"{item.brand} — {item.name}" if item.brand else item.name
    source_tag = (item.source or "?").upper()

    st.markdown(
        f"**{name_line}**  \n_{item.calories_per_unit} cal per {item.unit} · {source_tag}_"
    )
    if st.button("Pick this", key=f"pantry_pick_{idx}", use_container_width=True):
        # Persist the catalog row (idempotent on source+external_id) so
        # we have a stable id to stash in session state.
        from core.domain.models import CatalogIngredient
        catalog = catalog_repo.save(CatalogIngredient.from_food_item(item))
        st.session_state[_LINKED_CATALOG_ID_KEY] = catalog.id
        st.session_state[_LINKED_NAME_KEY] = catalog.display_name
        # Pre-clear the name input so the form will pick up the new
        # linked name on rerender (the form stash code re-fills only
        # when the input is empty).
        st.session_state.pop("pantry_name", None)
        st.rerun()
    st.divider()


def _clear_link_stash() -> None:
    """Clear the catalog-link session-state stash. Called both on
    'Clear link' button click and after a successful pantry add."""
    for k in (_LINKED_NAME_KEY, _LINKED_CATALOG_ID_KEY,
              _SEARCH_RESULTS_KEY, _LAST_QUERY_KEY,
              "pantry_link_query"):
        st.session_state.pop(k, None)
