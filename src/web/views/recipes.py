"""
Recipes page: list household recipes; planner can add, edit, delete, and
ask the food database to estimate calories.

Recipe ingredients are entered as one line per ingredient. Two formats are
accepted:
    name, quantity, unit
    name, quantity, unit, store
The 4-field form is what edits of seed recipes show by default so per-
ingredient store routing isn't lost when the planner tweaks something.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import List

import streamlit as st

from core.domain.models import Ingredient, Recipe
from core.domain.security import SecurityValidationError
from core.interfaces.user_repository import UserProfile
from core.services.recipe_nutrition_estimator import (
    NutritionEstimate,
    RecipeNutritionEstimator,
)
from repositories.sqlite.recipe_repository import SQLiteRecipeRepository


def render(user: UserProfile,
           repo: SQLiteRecipeRepository,
           estimator: RecipeNutritionEstimator) -> None:
    st.title("Recipes")
    st.caption(
        "Recipes are shared across your household. "
        + ("You can add, edit, and delete." if user.is_planner else "Only the planner can change them.")
    )

    if not user.household_id:
        st.warning("You're not in a household yet. Ask the planner for an invite code.")
        return

    _render_recipe_list(user, repo, estimator)
    if user.is_planner:
        st.divider()
        _render_add_recipe_form(user, repo)


def _render_recipe_list(user: UserProfile,
                        repo: SQLiteRecipeRepository,
                        estimator: RecipeNutritionEstimator) -> None:
    recipes = repo.find_all_by_household(user.household_id)
    if not recipes:
        st.info("No recipes yet. " + ("Add your first one below!" if user.is_planner else "Ask the planner to add some."))
        return

    editing_id = st.session_state.get("editing_recipe_id")
    for recipe in recipes:
        tier_chip = f"[{recipe.tier}] " if recipe.tier else ""
        cal_label = f"{recipe.calories_per_serving} cal/serving" if recipe.calories_per_serving else "calories TBD"
        header = f"**{tier_chip}{recipe.name}** — {cal_label} · serves {recipe.base_servings}"
        with st.expander(header):
            if editing_id == recipe.id and user.is_planner:
                _render_edit_form(user, repo, recipe)
            else:
                _render_recipe_card(user, repo, estimator, recipe)


def _render_recipe_card(user: UserProfile,
                        repo: SQLiteRecipeRepository,
                        estimator: RecipeNutritionEstimator,
                        recipe: Recipe) -> None:
    st.markdown("**Ingredients**")
    for ing in recipe.ingredients:
        store_chip = f" `{ing.store}`" if ing.store else ""
        if ing.quantity == 0:
            st.write(f"- {ing.name}{store_chip}")
        else:
            qty_str = _format_quantity(ing.quantity)
            st.write(f"- {qty_str} {ing.unit} {ing.name}{store_chip}")
    if recipe.instructions:
        st.markdown("**Instructions**")
        for i, step in enumerate(recipe.instructions, start=1):
            st.write(f"{i}. {step}")
    if recipe.notes:
        st.markdown("**Notes**")
        st.caption(recipe.notes)

    if not user.is_planner:
        return

    cols = st.columns(3)
    if cols[0].button("Edit", key=f"edit-{recipe.id}"):
        st.session_state.editing_recipe_id = recipe.id
        st.rerun()
    if cols[1].button("Estimate cal.", key=f"est-{recipe.id}"):
        st.session_state.estimate_for_recipe_id = recipe.id
        st.rerun()
    if cols[2].button("Delete", key=f"del-{recipe.id}", type="secondary"):
        repo.delete_by_name(recipe.name, user.household_id)
        st.rerun()

    if st.session_state.get("estimate_for_recipe_id") == recipe.id:
        _render_estimate_panel(repo, estimator, recipe, user.household_id)


def _format_quantity(qty: Decimal) -> str:
    """Render a Decimal without trailing zeros."""
    normalized = qty.normalize()
    return f"{normalized:f}" if normalized == normalized.to_integral_value() else str(normalized)


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


def _render_edit_form(user: UserProfile,
                      repo: SQLiteRecipeRepository,
                      recipe: Recipe) -> None:
    """Pre-populated edit form for an existing recipe."""
    # Build the current ingredients text in 4-field format so store routing is preserved.
    def _ing_line(ing: Ingredient) -> str:
        qty = _format_quantity(ing.quantity)
        base = f"{ing.name}, {qty}, {ing.unit}"
        return f"{base}, {ing.store}" if ing.store else base

    default_ingredients = "\n".join(_ing_line(ing) for ing in recipe.ingredients)
    default_instructions = "\n".join(recipe.instructions)

    with st.form(f"edit_recipe_{recipe.id}"):
        name = st.text_input("Recipe name", value=recipe.name).strip()
        col1, col2 = st.columns(2)
        with col1:
            base_servings = st.number_input(
                "Servings", min_value=1, max_value=50,
                value=recipe.base_servings, step=1,
            )
        with col2:
            calories_per_serving = st.number_input(
                "Calories per serving", min_value=0, max_value=5000,
                value=recipe.calories_per_serving or 0, step=10,
            )
        st.caption("Ingredients (one per line: `name, quantity, unit` or `name, quantity, unit, store`)")
        ingredients_raw = st.text_area("Ingredients", value=default_ingredients, height=150)
        st.caption("Instructions (one step per line, leave blank if none)")
        instructions_raw = st.text_area("Instructions", value=default_instructions, height=120)
        tier = st.selectbox(
            "Tier",
            options=["", "S", "A", "B", "C"],
            index=["", "S", "A", "B", "C"].index(recipe.tier or ""),
        )
        notes = st.text_area("Notes", value=recipe.notes or "", height=80)

        col_save, col_cancel = st.columns(2)
        save = col_save.form_submit_button("Save changes", type="primary")
        cancel = col_cancel.form_submit_button("Cancel")

    if cancel:
        st.session_state.pop("editing_recipe_id", None)
        st.rerun()

    if not save:
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

    steps = [s.strip() for s in instructions_raw.splitlines() if s.strip()]

    try:
        recipe.name = name
        recipe.base_servings = int(base_servings)
        recipe.calories_per_serving = int(calories_per_serving)
        recipe.ingredients = ingredients
        recipe.instructions = steps
        recipe.tier = tier or None
        recipe.notes = notes.strip() or None
        result = repo.update(recipe, household_id=user.household_id)
    except SecurityValidationError as e:
        st.error(f"Invalid input: {e}")
        return

    if result is None:
        st.error("Could not save — recipe not found.")
        return

    st.success(f"Updated '{result.name}'.")
    st.session_state.pop("editing_recipe_id", None)
    st.session_state.pop("estimate_for_recipe_id", None)
    st.rerun()


def _render_estimate_panel(repo: SQLiteRecipeRepository,
                           estimator,
                           recipe: Recipe,
                           household_id: str) -> None:
    """Show a calorie estimate breakdown and let the planner save it to the recipe."""
    st.divider()
    st.markdown("**Calorie estimate**")

    with st.spinner("Estimating…"):
        try:
            result: NutritionEstimate = estimator.estimate(recipe)
        except Exception as e:
            st.error(f"Estimation failed: {e}")
            return

    # Per-ingredient table.
    rows = []
    for est in result.estimates:
        if est.estimated_calories is not None:
            rows.append({"Ingredient": est.ingredient_name,
                         "Matched as": est.matched_food or "—",
                         "Calories": est.estimated_calories})
        else:
            rows.append({"Ingredient": est.ingredient_name,
                         "Matched as": f"skipped — {est.skip_reason}",
                         "Calories": "—"})
    st.table(rows)

    st.write(f"**Total: {result.total_calories} cal "
             f"({result.total_calories_per_serving} cal / serving)**")
    if result.skipped_count:
        st.caption(f"{result.skipped_count} ingredient(s) skipped (see table above). "
                   "Actual calories will be higher.")

    col_save, col_dismiss = st.columns(2)
    if col_save.button("Save estimate to recipe", key=f"save-est-{recipe.id}"):
        recipe.calories_per_serving = result.total_calories_per_serving
        repo.update(recipe, household_id=household_id)
        st.success(f"Saved {result.total_calories_per_serving} cal/serving.")
        st.session_state.pop("estimate_for_recipe_id", None)
        st.rerun()
    if col_dismiss.button("Dismiss", key=f"dismiss-est-{recipe.id}"):
        st.session_state.pop("estimate_for_recipe_id", None)
        st.rerun()


def _parse_ingredients(raw: str) -> List[Ingredient]:
    """Parse a multi-line block of ingredient entries.

    Accepted formats per line:
        name, quantity, unit
        name, quantity, unit, store
    """
    ingredients: List[Ingredient] = []
    for lineno, line in enumerate(raw.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) == 3:
            ing_name, qty_str, unit = parts
            store = None
        elif len(parts) == 4:
            ing_name, qty_str, unit, store = parts
            store = store or None
        else:
            raise ValueError(
                f"Line {lineno}: expected 'name, quantity, unit' or "
                f"'name, quantity, unit, store' (got: {line!r})"
            )
        try:
            qty = Decimal(qty_str)
        except InvalidOperation:
            raise ValueError(f"Line {lineno}: quantity '{qty_str}' is not a number")
        try:
            ingredients.append(Ingredient(name=ing_name, quantity=qty, unit=unit, store=store))
        except SecurityValidationError as e:
            raise ValueError(f"Line {lineno}: {e}")
    if not ingredients:
        raise ValueError("Please list at least one ingredient.")
    return ingredients
