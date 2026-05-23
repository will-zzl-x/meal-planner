"""
Recipes page (slice 8b refresh): the planner builds and edits recipes by
searching real nutrition databases and picking ingredients with known
per-serving calories. The recipe's calories per serving is then a live
sum of (servings × catalog calories) across its ingredient list — never
typed in by hand.

Old "estimator" pathway is gone. Old recipes that haven't yet been
re-saved through the picker still display whatever calorie figure they
were created with; the planner can re-edit them through the new form
to lock in real nutrition (slice 8e backfill will do the seed batch).
"""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

import streamlit as st

from core.domain.models import CatalogIngredient, Ingredient, Recipe
from core.domain.security import SecurityValidationError
from core.interfaces.user_repository import UserProfile
from core.services.food_database_service import FoodDatabaseService
from core.services.pantry_coverage_service import (
    CoverageReport,
    PantryCoverageService,
)
from core.services.recipe_calorie_calculator import RecipeCalorieCalculator
from repositories.sqlite.ingredient_catalog_repository import (
    SQLiteIngredientCatalogRepository,
)
from repositories.sqlite.recipe_repository import SQLiteRecipeRepository
from web.views.food_picker import render_food_picker


# Filter options for the Recipes page coverage filter (V2-7).
_COVERAGE_THRESHOLDS = {
    "Show all": 0.0,
    "Coverage ≥ 50%": 0.5,
    "Coverage ≥ 80%": 0.8,
    "Only 100%": 1.0,
}


def render(user: UserProfile,
           recipe_repo: SQLiteRecipeRepository,
           food_db: FoodDatabaseService,
           catalog_repo: SQLiteIngredientCatalogRepository,
           calorie_calc: RecipeCalorieCalculator,
           coverage_svc: PantryCoverageService) -> None:
    st.title("Recipes")
    st.caption(
        "Recipes are shared across your household. "
        + ("You can add, edit, and delete." if user.is_planner else "Only the planner can change them.")
    )

    if not user.household_id:
        st.warning("You're not in a household yet. Ask the planner for an invite code.")
        return

    _render_recipe_list(user, recipe_repo, food_db, catalog_repo, calorie_calc, coverage_svc)
    if user.is_planner:
        st.divider()
        _render_add_recipe(user, recipe_repo, food_db, catalog_repo, calorie_calc)


# ------------------------------------------------------------------ list view

def _render_recipe_list(user: UserProfile,
                        recipe_repo: SQLiteRecipeRepository,
                        food_db: FoodDatabaseService,
                        catalog_repo: SQLiteIngredientCatalogRepository,
                        calorie_calc: RecipeCalorieCalculator,
                        coverage_svc: PantryCoverageService) -> None:
    recipes = recipe_repo.find_all_by_household(user.household_id)
    if not recipes:
        st.info("No recipes yet. " + ("Add your first one below!" if user.is_planner else "Ask the planner to add some."))
        return

    # V2-7: filter / sort controls. Persist user choices in session state
    # so they survive reruns when the user adds/removes a recipe.
    treat_staples, threshold_label, sort_by_cov = _render_filter_row()
    threshold = _COVERAGE_THRESHOLDS[threshold_label]

    # Compute coverage once per recipe; results drive both the chip in
    # the header and the missing-list inside the card. Pair with each
    # recipe so we can sort and filter without re-computing.
    decorated = []
    for recipe in recipes:
        coverage = coverage_svc.compute_coverage(
            recipe, user.household_id,
            treat_staples_as_available=treat_staples,
        )
        decorated.append((recipe, coverage))

    # Apply filter. A recipe with zero catalog-backed ingredients
    # (legacy / unedited seeds) has total_count == 0 — skip the
    # filter for those so they always show ("we don't know enough to
    # exclude them"). Filtering them out aggressively would hide
    # everything the first time a user lands here.
    if threshold > 0:
        decorated = [
            (r, c) for r, c in decorated
            if c.total_count == 0 or c.coverage_ratio >= threshold
        ]

    if sort_by_cov:
        # Highest coverage first; recipes with no data sink to the bottom.
        decorated.sort(
            key=lambda rc: (
                -rc[1].coverage_ratio if rc[1].total_count else -(-1.0),
                rc[0].name.lower(),
            )
        )

    if not decorated:
        st.info(
            "No recipes match that pantry coverage. Try lowering the "
            "threshold or update the pantry on the Pantry page."
        )
        return

    editing_id = st.session_state.get("editing_recipe_id")
    for recipe, coverage in decorated:
        breakdown = calorie_calc.compute(recipe)
        # Live-computed calories take precedence; only fall back to the stored
        # number for legacy recipes that haven't been re-saved through the picker.
        cal_per_serving = (
            breakdown.calories_per_serving
            if breakdown.lines
            else recipe.calories_per_serving
        )
        cal_label = f"{cal_per_serving} cal/serving" if cal_per_serving else "calories TBD"
        coverage_chip = _format_coverage_chip(coverage)
        header_parts = [f"**{recipe.name}**", cal_label]
        if coverage_chip:
            header_parts.append(coverage_chip)
        header_parts.append(f"serves {recipe.base_servings}")
        header = " — ".join(header_parts[:2]) + " · " + " · ".join(header_parts[2:])
        with st.expander(header):
            if editing_id == recipe.id and user.is_planner:
                _render_edit_recipe(user, recipe_repo, food_db, catalog_repo,
                                    calorie_calc, recipe)
            else:
                _render_recipe_card(user, recipe_repo, recipe, breakdown, coverage)


def _render_filter_row() -> tuple:
    """Render the staples / coverage-threshold / sort controls and return
    the user's current choices. Stored under stable session-state keys so
    they survive across reruns."""
    cols = st.columns([3, 3, 2])
    threshold_label = cols[0].selectbox(
        "Pantry coverage", options=list(_COVERAGE_THRESHOLDS.keys()),
        index=0, key="recipes_filter_threshold",
    )
    treat_staples = cols[1].checkbox(
        "Treat staples (salt, oil, etc.) as on hand",
        value=True, key="recipes_filter_staples",
    )
    sort_by_cov = cols[2].checkbox(
        "Sort by coverage", value=False, key="recipes_filter_sort",
    )
    return treat_staples, threshold_label, sort_by_cov


def _format_coverage_chip(coverage: CoverageReport) -> str:
    """Short string like '8/11 in pantry' for the recipe header. Empty
    string when there's nothing meaningful to show (legacy recipe with
    no catalog-backed ingredients)."""
    total = coverage.total_count
    if total == 0:
        return ""
    if coverage.have_count == total:
        return "all in pantry"
    return f"{coverage.have_count}/{total} in pantry"


def _render_recipe_card(user: UserProfile,
                        recipe_repo: SQLiteRecipeRepository,
                        recipe: Recipe,
                        breakdown,
                        coverage: CoverageReport) -> None:
    if recipe.image_url:
        # use_container_width so the image scales naturally on phone & desktop;
        # a bad/dead URL renders as Streamlit's broken-image icon — acceptable
        # for V1 since we don't host or validate the link.
        st.image(recipe.image_url, use_container_width=True)
    st.markdown("**Ingredients**")
    if breakdown.lines:
        for line in breakdown.lines:
            store_chip = ""
            st.write(
                f"- {_fmt_decimal(line.servings)} × {line.name} "
                f"({line.serving_label}) — {line.line_calories} cal{store_chip}"
            )
        st.caption(
            f"Total: {breakdown.total_calories} cal "
            f"({breakdown.calories_per_serving} per serving)"
        )
        if breakdown.unaccounted_count:
            st.caption(
                f"_{breakdown.unaccounted_count} ingredient(s) without nutrition info — "
                "edit and re-add them through search to include calories._"
            )
    else:
        # Legacy recipe — show free-text ingredients without per-line calories.
        for ing in recipe.ingredients:
            qty = _fmt_decimal(ing.quantity)
            store = f" `{ing.store}`" if ing.store else ""
            st.write(f"- {qty} {ing.unit} {ing.name}{store}")
        st.caption("_Stored calorie figure — edit through search to compute from real data._")

    # V2-6: pantry coverage block. Only meaningful when we have catalog-
    # backed ingredients to compare against; legacy recipes get nothing here.
    if coverage.total_count > 0:
        if coverage.have_count == coverage.total_count:
            st.markdown("**Pantry coverage**")
            st.caption("_All ingredients in pantry._")
        elif coverage.missing_lines:
            st.markdown("**Missing from pantry**")
            for line in coverage.missing_lines:
                # Use the catalog display name for clarity; the user-typed
                # ingredient name is on the line above already.
                shown_name = line.catalog_display_name or line.ingredient_name
                if line.status == "short" and line.deficit is not None:
                    st.write(
                        f"- {shown_name} — short by {_fmt_decimal(line.deficit)} "
                        f"serving(s)"
                    )
                else:
                    st.write(f"- {shown_name}")

    if recipe.instructions:
        st.markdown("**Instructions**")
        for i, step in enumerate(recipe.instructions, start=1):
            st.write(f"{i}. {step}")
    if recipe.notes:
        st.markdown("**Notes**")
        st.caption(recipe.notes)

    if not user.is_planner:
        return

    cols = st.columns(2)
    if cols[0].button("Edit", key=f"edit-{recipe.id}"):
        st.session_state.editing_recipe_id = recipe.id
        st.rerun()
    if cols[1].button("Delete", key=f"del-{recipe.id}", type="secondary"):
        recipe_repo.delete_by_name(recipe.name, user.household_id)
        st.rerun()


# ------------------------------------------------------------------ add form

def _render_add_recipe(user: UserProfile,
                       recipe_repo: SQLiteRecipeRepository,
                       food_db: FoodDatabaseService,
                       catalog_repo: SQLiteIngredientCatalogRepository,
                       calorie_calc: RecipeCalorieCalculator) -> None:
    st.subheader("Add a recipe")
    draft_key = "draft_new_recipe"
    drafts: List[_DraftIngredient] = st.session_state.setdefault(draft_key, [])

    st.markdown("**Step 1 — Add ingredients via search**")
    render_food_picker(
        widget_key="add_picker",
        food_db=food_db,
        catalog_repo=catalog_repo,
        on_pick=lambda c, s, store: _append_draft(draft_key, c, s, store),
    )

    if drafts:
        st.markdown("**Currently in this recipe**")
        _render_draft_list(draft_key, drafts)
        running_total = sum(int(round(float(d.servings) * d.calories_per_serving)) for d in drafts)
        st.caption(f"Running total: {running_total} cal (will divide by servings on save)")

    st.markdown("**Step 2 — Recipe details**")
    with st.form("add_recipe_form", clear_on_submit=False):
        name = st.text_input("Recipe name").strip()
        base_servings = st.number_input("Servings", min_value=1, max_value=50, value=1, step=1)
        image_url = st.text_input(
            "Image URL (optional)",
            placeholder="https://… link to a photo of the finished dish",
        ).strip()
        instructions_raw = st.text_area("Instructions (one step per line)", height=120)
        notes = st.text_area("Notes (optional)", height=80)
        submitted = st.form_submit_button("Save recipe", type="primary")

    if not submitted:
        return
    if not name:
        st.error("Recipe name is required.")
        return
    if not drafts:
        st.error("Add at least one ingredient via search above.")
        return

    try:
        recipe = Recipe(
            name=name,
            ingredients=_drafts_to_ingredients(drafts),
            base_servings=int(base_servings),
            calories_per_serving=_per_serving_total(drafts, int(base_servings)),
            instructions=[s.strip() for s in instructions_raw.splitlines() if s.strip()],
            notes=notes.strip() or None,
            image_url=image_url or None,
        )
        recipe_repo.save(recipe, household_id=user.household_id, created_by_user_id=user.user_id)
    except SecurityValidationError as e:
        st.error(f"Invalid input: {e}")
        return

    st.success(f"Added '{name}'.")
    _clear_draft(draft_key)
    st.rerun()


# ------------------------------------------------------------------ edit form

def _render_edit_recipe(user: UserProfile,
                        recipe_repo: SQLiteRecipeRepository,
                        food_db: FoodDatabaseService,
                        catalog_repo: SQLiteIngredientCatalogRepository,
                        calorie_calc: RecipeCalorieCalculator,
                        recipe: Recipe) -> None:
    draft_key = f"draft_edit_recipe_{recipe.id}"
    if draft_key not in st.session_state:
        # Seed from existing ingredients on first render of this edit session.
        st.session_state[draft_key] = _build_initial_drafts(recipe, catalog_repo)
    drafts: List[_DraftIngredient] = st.session_state[draft_key]

    st.markdown("**Add or replace ingredients via search**")
    render_food_picker(
        widget_key=f"edit_picker_{recipe.id}",
        food_db=food_db,
        catalog_repo=catalog_repo,
        on_pick=lambda c, s, store: _append_draft(draft_key, c, s, store),
    )

    st.markdown("**Currently in this recipe**")
    if drafts:
        _render_draft_list(draft_key, drafts)
        running_total = sum(int(round(float(d.servings) * d.calories_per_serving)) for d in drafts)
        st.caption(f"Running total: {running_total} cal")
    else:
        st.caption("_No ingredients in the recipe yet — add some via search above._")

    with st.form(f"edit_recipe_form_{recipe.id}", clear_on_submit=False):
        name = st.text_input("Recipe name", value=recipe.name).strip()
        base_servings = st.number_input(
            "Servings", min_value=1, max_value=50,
            value=recipe.base_servings, step=1,
        )
        image_url = st.text_input(
            "Image URL (optional)",
            value=recipe.image_url or "",
            placeholder="https://… link to a photo of the finished dish",
        ).strip()
        instructions_raw = st.text_area(
            "Instructions (one step per line)",
            value="\n".join(recipe.instructions), height=120,
        )
        notes = st.text_area("Notes (optional)", value=recipe.notes or "", height=80)
        col_save, col_cancel = st.columns(2)
        save = col_save.form_submit_button("Save changes", type="primary")
        cancel = col_cancel.form_submit_button("Cancel")

    if cancel:
        _clear_draft(draft_key)
        st.session_state.pop("editing_recipe_id", None)
        st.rerun()

    if not save:
        return
    if not name:
        st.error("Recipe name is required.")
        return
    if not drafts:
        st.error("Recipe needs at least one ingredient.")
        return

    try:
        recipe.name = name
        recipe.ingredients = _drafts_to_ingredients(drafts)
        recipe.base_servings = int(base_servings)
        recipe.calories_per_serving = _per_serving_total(drafts, int(base_servings))
        recipe.instructions = [s.strip() for s in instructions_raw.splitlines() if s.strip()]
        recipe.notes = notes.strip() or None
        recipe.image_url = image_url or None
        result = recipe_repo.update(recipe, household_id=user.household_id)
    except SecurityValidationError as e:
        st.error(f"Invalid input: {e}")
        return

    if result is None:
        st.error("Could not save — recipe not found.")
        return
    st.success(f"Updated '{result.name}'.")
    _clear_draft(draft_key)
    st.session_state.pop("editing_recipe_id", None)
    st.rerun()


# ------------------------------------------------------------------ draft helpers

class _DraftIngredient:
    """Lightweight in-memory record of a picker-added ingredient. Held in
    session state until the form is saved.

    `store` is the optional per-ingredient store routing label (e.g.
    "Costco", "Walmart") — preserved so picker-saved recipes don't
    silently lose the grocery-list-routing info that seed recipes had.
    """
    __slots__ = ("catalog_id", "display_name", "serving_label",
                 "calories_per_serving", "servings", "store")

    def __init__(self, catalog: CatalogIngredient, servings: Decimal,
                 store: Optional[str] = None):
        self.catalog_id = catalog.id
        self.display_name = catalog.display_name
        self.serving_label = catalog.serving_label
        self.calories_per_serving = catalog.calories_per_serving
        self.servings = servings
        self.store = store


def _append_draft(draft_key: str, catalog: CatalogIngredient, servings: Decimal,
                  store: Optional[str] = None) -> None:
    drafts: List[_DraftIngredient] = st.session_state.setdefault(draft_key, [])
    drafts.append(_DraftIngredient(catalog, servings, store))


def _clear_draft(draft_key: str) -> None:
    st.session_state.pop(draft_key, None)


def _render_draft_list(draft_key: str, drafts: List[_DraftIngredient]) -> None:
    """Render each draft ingredient with a remove button."""
    for idx, draft in enumerate(drafts):
        line_cal = int(round(float(draft.servings) * draft.calories_per_serving))
        # Wider Remove column + use_container_width so the button has
        # a reasonable tap target on a phone.
        cols = st.columns([5, 2])
        cols[0].write(
            f"- {_fmt_decimal(draft.servings)} × {draft.display_name} "
            f"({draft.serving_label}) — {line_cal} cal"
        )
        if cols[1].button("Remove", key=f"{draft_key}_rm_{idx}",
                          use_container_width=True):
            drafts.pop(idx)
            st.rerun()


def _build_initial_drafts(recipe: Recipe,
                          catalog_repo: SQLiteIngredientCatalogRepository) -> List[_DraftIngredient]:
    """Pre-populate edit drafts from a recipe's catalog-backed ingredients.
    Legacy free-text ingredients are skipped so the planner re-picks them
    through search (where they get real nutrition)."""
    drafts: List[_DraftIngredient] = []
    for ing in recipe.ingredients:
        if not (ing.catalog_ingredient_id and ing.servings is not None):
            continue
        catalog = catalog_repo.find_by_id(ing.catalog_ingredient_id)
        if catalog is None:
            continue
        drafts.append(_DraftIngredient(catalog, ing.servings, ing.store))
    return drafts


def _drafts_to_ingredients(drafts: List[_DraftIngredient]) -> List[Ingredient]:
    """Convert the in-memory draft rows into Ingredient records the recipe
    repo can persist. We set name/quantity/unit for compatibility with the
    legacy fields and also populate catalog_ingredient_id + servings so the
    calorie calculator can reuse the link on read. `store` is preserved so
    picker-saved recipes can be routed by the grocery list."""
    return [
        Ingredient(
            name=d.display_name,
            quantity=d.servings,
            unit=d.serving_label,
            store=d.store,
            catalog_ingredient_id=d.catalog_id,
            servings=d.servings,
        )
        for d in drafts
    ]


def _per_serving_total(drafts: List[_DraftIngredient], servings: int) -> int:
    total = sum(int(round(float(d.servings) * d.calories_per_serving)) for d in drafts)
    return int(round(total / servings)) if servings > 0 else 0


def _fmt_decimal(qty: Decimal) -> str:
    normalized = qty.normalize()
    return f"{normalized:f}" if normalized == normalized.to_integral_value() else str(normalized)
