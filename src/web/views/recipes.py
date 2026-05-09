"""
Recipes page: list household recipes; planner can add and delete.

Recipe ingredients are entered as one line per ingredient in the form
    name, quantity, unit
to keep the V1 UI simple. Lines are validated against the domain
SecurityValidationError so users get a clear message on bad input.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import List, Tuple

import streamlit as st

from core.domain.models import Ingredient, Recipe
from core.domain.security import SecurityValidationError
from core.interfaces.user_repository import UserProfile
from repositories.sqlite.recipe_repository import SQLiteRecipeRepository


def render(user: UserProfile, repo: SQLiteRecipeRepository) -> None:
    st.title("Recipes")
    st.caption(f"Recipes are shared across your household. {'You can add and delete.' if user.is_planner else 'Only the planner can add or delete.'}")

    if not user.household_id:
        st.warning("You're not in a household yet. Ask the planner for an invite code.")
        return

    _render_recipe_list(user, repo)
    if user.is_planner:
        st.divider()
        _render_add_recipe_form(user, repo)


def _render_recipe_list(user: UserProfile, repo: SQLiteRecipeRepository) -> None:
    recipes = repo.find_all_by_household(user.household_id)
    if not recipes:
        st.info("No recipes yet. " + ("Add your first one below!" if user.is_planner else "Ask the planner to add some."))
        return

    for recipe in recipes:
        with st.expander(f"**{recipe.name}** — {recipe.calories_per_serving} cal/serving · serves {recipe.base_servings}"):
            for ing in recipe.ingredients:
                st.write(f"- {ing.quantity} {ing.unit} {ing.name}")
            if user.is_planner:
                if st.button("Delete", key=f"delete-{recipe.name}", type="secondary"):
                    repo.delete_by_name(recipe.name, user.household_id)
                    st.rerun()


def _render_add_recipe_form(user: UserProfile, repo: SQLiteRecipeRepository) -> None:
    st.subheader("Add a recipe")
    with st.form("add_recipe", clear_on_submit=True):
        name = st.text_input("Recipe name").strip()
        col1, col2 = st.columns(2)
        with col1:
            base_servings = st.number_input("Servings", min_value=1, max_value=50, value=1, step=1)
        with col2:
            calories_per_serving = st.number_input("Calories per serving", min_value=0, max_value=5000, value=400, step=10)
        st.caption("Ingredients (one per line, format: `name, quantity, unit`)")
        ingredients_raw = st.text_area("Ingredients", placeholder="chicken breast, 6, oz\nrice, 1, cup")
        submit = st.form_submit_button("Add recipe")

    if not submit:
        return
    if not name:
        st.error("Recipe name is required.")
        return
    if not ingredients_raw.strip():
        st.error("Please list at least one ingredient.")
        return

    try:
        ingredients = _parse_ingredients(ingredients_raw)
    except ValueError as e:
        st.error(str(e))
        return

    try:
        recipe = Recipe(
            name=name,
            ingredients=ingredients,
            base_servings=int(base_servings),
            calories_per_serving=int(calories_per_serving),
        )
        repo.save(recipe, household_id=user.household_id, created_by_user_id=user.user_id)
    except SecurityValidationError as e:
        st.error(f"Invalid input: {e}")
        return

    st.success(f"Added '{name}'.")
    st.rerun()


def _parse_ingredients(raw: str) -> List[Ingredient]:
    """Parse a multi-line block of `name, quantity, unit` entries into Ingredients."""
    ingredients: List[Ingredient] = []
    for lineno, line in enumerate(raw.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 3:
            raise ValueError(
                f"Line {lineno}: expected 'name, quantity, unit' (got: {line!r})"
            )
        ing_name, qty_str, unit = parts
        try:
            qty = Decimal(qty_str)
        except InvalidOperation:
            raise ValueError(f"Line {lineno}: quantity '{qty_str}' is not a number")
        try:
            ingredients.append(Ingredient(name=ing_name, quantity=qty, unit=unit))
        except SecurityValidationError as e:
            raise ValueError(f"Line {lineno}: {e}")
    if not ingredients:
        raise ValueError("Please list at least one ingredient.")
    return ingredients
