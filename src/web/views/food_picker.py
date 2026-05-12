"""
Reusable food-search-and-pick widget.

Anywhere the app needs the user to attach a food item with known nutrition
(building a recipe ingredient list, logging today's intake, etc.), it
calls `render_food_picker`. The picker:

1. Shows a search box; when the user submits, queries
   FoodDatabaseService (USDA + Open Food Facts + offline sample DB).
2. Displays each result with name, brand, serving label, and calories.
3. Lets the user enter a servings count (and optionally a per-ingredient
   store) and click "Add". On click we cache the picked item into the
   local ingredients catalog (so future loads don't re-fetch) and invoke
   a caller-supplied `on_pick` callback with the persisted
   CatalogIngredient + servings + store.

Caller is responsible for providing a stable `widget_key` so multiple
pickers on the same page don't collide on session state.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Callable, Optional

import streamlit as st

from core.domain.models import CatalogIngredient, FoodItem
from core.services.food_database_service import FoodDatabaseService
from repositories.sqlite.ingredient_catalog_repository import (
    SQLiteIngredientCatalogRepository,
)


def render_food_picker(
    *,
    widget_key: str,
    food_db: FoodDatabaseService,
    catalog_repo: SQLiteIngredientCatalogRepository,
    on_pick: Callable[[CatalogIngredient, Decimal, Optional[str]], None],
    label: str = "Search foods",
    placeholder: str = "e.g. chicken thigh, brown rice, Chobani yogurt",
    show_store: bool = True,
) -> None:
    """Render the search-and-add UI. Calls
    `on_pick(catalog_item, servings, store_or_none)` each time the user
    clicks Add on a result.

    `show_store` controls whether each result row exposes a per-ingredient
    store input. Recipes use it (grocery routing matters); the food log
    leaves it off (no use for it on logged meals).
    """
    results_key = f"{widget_key}_results"
    query_key = f"{widget_key}_query"
    last_query_key = f"{widget_key}_last_query"

    with st.form(f"{widget_key}_form", clear_on_submit=False):
        query = st.text_input(label, placeholder=placeholder, key=query_key)
        searched = st.form_submit_button("Search")

    if searched and query.strip():
        with st.spinner("Searching food databases…"):
            st.session_state[results_key] = food_db.search_food_database(
                query.strip(), limit=15,
            )
        st.session_state[last_query_key] = query.strip()

    results = st.session_state.get(results_key) or []
    last_query = st.session_state.get(last_query_key)

    # Empty-results feedback: only after at least one search has run, so
    # we don't shout "no results" before the user even searches.
    if last_query and not results:
        st.caption(
            f"No matches for '{last_query}' in USDA, Open Food Facts, or "
            "the offline list. Try a simpler query (e.g. 'rice' instead of "
            "'short grain Japanese rice'), or add it manually below."
        )
        # Manual fallback is most useful here — let the user add the
        # missing item with their own nutrition figure.
        _render_manual_form(
            widget_key=widget_key,
            catalog_repo=catalog_repo,
            on_pick=on_pick,
            show_store=show_store,
        )
        return
    if not results:
        return

    st.caption(f"{len(results)} result(s). Pick one and choose servings to add.")
    for idx, item in enumerate(results):
        _render_result_row(
            item=item,
            row_key=f"{widget_key}_row_{idx}",
            catalog_repo=catalog_repo,
            on_pick=on_pick,
            show_store=show_store,
        )

    # Manual fallback also offered when results exist — the catalog
    # might not include the specific brand the user wants.
    _render_manual_form(
        widget_key=widget_key,
        catalog_repo=catalog_repo,
        on_pick=on_pick,
        show_store=show_store,
    )


def _render_manual_form(*,
                        widget_key: str,
                        catalog_repo: SQLiteIngredientCatalogRepository,
                        on_pick: Callable[[CatalogIngredient, Decimal, Optional[str]], None],
                        show_store: bool) -> None:
    with st.expander("None of these match? Add manually"):
        st.caption(
            "For foods the databases don't cover. The number you enter is "
            "calories per *one serving* of whatever serving label you choose "
            "(e.g. '1 slice', '100g', '1 medium banana')."
        )
        with st.form(f"{widget_key}_manual_form", clear_on_submit=False):
            name = st.text_input("Name", key=f"{widget_key}_manual_name").strip()
            col1, col2 = st.columns(2)
            with col1:
                serving_label = st.text_input(
                    "Serving label", value="100g",
                    key=f"{widget_key}_manual_label",
                ).strip()
            with col2:
                cal_per_serving = st.number_input(
                    "Calories per serving", min_value=0, max_value=5000,
                    value=0, step=10,
                    key=f"{widget_key}_manual_cal",
                )
            servings_str = st.text_input(
                "How many servings?", value="1",
                key=f"{widget_key}_manual_servings",
            )
            store_value = ""
            if show_store:
                store_value = st.text_input(
                    "Store (optional)", value="",
                    key=f"{widget_key}_manual_store",
                ).strip()
            submitted = st.form_submit_button("Add manually")

        if not submitted:
            return
        if not name:
            st.error("Name is required.")
            return
        servings = _parse_servings(servings_str)
        if servings is None:
            st.error("Servings must be a positive number.")
            return
        if not serving_label:
            st.error("Serving label can't be empty.")
            return

        catalog = catalog_repo.save(CatalogIngredient(
            id="",
            name=name,
            serving_label=serving_label,
            calories_per_serving=int(cal_per_serving),
            source="manual",
            external_id=None,
        ))
        on_pick(catalog, servings, store_value or None)
        # Clear the form's session-state values on success.
        for k in (f"{widget_key}_manual_name", f"{widget_key}_manual_label",
                  f"{widget_key}_manual_cal", f"{widget_key}_manual_servings",
                  f"{widget_key}_manual_store"):
            st.session_state.pop(k, None)


def _render_result_row(*,
                       item: FoodItem,
                       row_key: str,
                       catalog_repo: SQLiteIngredientCatalogRepository,
                       on_pick: Callable[[CatalogIngredient, Decimal, Optional[str]], None],
                       show_store: bool) -> None:
    name_line = item.name
    if item.brand:
        name_line = f"{item.brand} — {item.name}"
    source_tag = (item.source or "?").upper()

    # Vertical stacking: name + nutrition spans the full width on its own
    # line so long catalog names ("Yogurt, Greek, plain, nonfat") aren't
    # squeezed into a 60% column. The controls live on a second row where
    # each control gets meaningful width on a 375 px iPhone screen.
    st.markdown(
        f"**{name_line}**  \n_{item.calories_per_unit} cal per {item.unit} · {source_tag}_"
    )

    if show_store:
        servings_col, store_col, add_col = st.columns([2, 2, 1])
    else:
        servings_col, add_col = st.columns([2, 1])
        store_col = None

    servings_str = servings_col.text_input(
        "Servings", value="1", key=f"{row_key}_servings", label_visibility="collapsed",
        placeholder="Servings",
    )
    store_value: Optional[str] = None
    if store_col is not None:
        store_value = store_col.text_input(
            "Store", value="", key=f"{row_key}_store", label_visibility="collapsed",
            placeholder="Store (optional)",
        ).strip() or None

    if add_col.button("Add", key=f"{row_key}_add", use_container_width=True):
        servings = _parse_servings(servings_str)
        if servings is None:
            st.warning("Servings must be a positive number.")
            return
        catalog = catalog_repo.save(CatalogIngredient.from_food_item(item))
        on_pick(catalog, servings, store_value)

    # Visual separator so adjacent rows don't blend together when the
    # name line is long enough to wrap.
    st.divider()


def _parse_servings(s: str) -> Optional[Decimal]:
    """Parse a servings input string into a positive Decimal, or return
    None if the input is empty / not a number / not positive."""
    try:
        value = Decimal((s or "").strip())
    except InvalidOperation:
        return None
    if value <= 0:
        return None
    return value
