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

    with st.form(f"{widget_key}_form", clear_on_submit=False):
        query = st.text_input(label, placeholder=placeholder, key=query_key)
        searched = st.form_submit_button("Search")

    if searched and query.strip():
        with st.spinner("Searching food databases…"):
            st.session_state[results_key] = food_db.search_food_database(
                query.strip(), limit=15,
            )

    results = st.session_state.get(results_key) or []
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

    # Layout: name / servings / [store?] / Add. The unit is shown inline
    # in the name line ("X cal per Y") so we drop the redundant "× unit"
    # caption that previous versions had — saves precious horizontal space.
    if show_store:
        cols = st.columns([5, 2, 2, 1])
        name_col, servings_col, store_col, add_col = cols
    else:
        cols = st.columns([5, 2, 1])
        name_col, servings_col, add_col = cols
        store_col = None

    name_col.markdown(
        f"**{name_line}**  \n_{item.calories_per_unit} cal per {item.unit} · {source_tag}_"
    )
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

    if add_col.button("Add", key=f"{row_key}_add"):
        servings = _parse_servings(servings_str)
        if servings is None:
            st.warning("Servings must be a positive number.")
            return
        catalog = catalog_repo.save(CatalogIngredient.from_food_item(item))
        on_pick(catalog, servings, store_value)


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
