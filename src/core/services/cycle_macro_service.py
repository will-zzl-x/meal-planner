"""
CycleMacroService — daily and cycle-wide totals (calories + macros) for
the meals planned in a cycle. Powers the "Macros at a glance" view on
the Plan page.

A cycle entry contributes `planned_servings × per_serving_*` to the day
it falls on. Recipes without catalog-backed ingredients contribute only
their stored calorie figure (macros = 0); the view labels those rows so
the user knows the macro picture is incomplete.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List

from core.domain.models import Recipe
from core.interfaces.meal_plan_repository import MealPlanEntry
from core.services.recipe_calorie_calculator import RecipeCalorieCalculator


@dataclass
class DayMacros:
    day: date
    calories: int = 0
    protein: Decimal = field(default_factory=lambda: Decimal("0"))
    carbs: Decimal = field(default_factory=lambda: Decimal("0"))
    fat: Decimal = field(default_factory=lambda: Decimal("0"))
    unaccounted_entries: int = 0  # entries whose macros are unknown


@dataclass
class CycleMacroSummary:
    days: List[DayMacros]

    @property
    def total_calories(self) -> int:
        return sum(d.calories for d in self.days)

    @property
    def total_protein(self) -> Decimal:
        return sum((d.protein for d in self.days), Decimal("0"))

    @property
    def total_carbs(self) -> Decimal:
        return sum((d.carbs for d in self.days), Decimal("0"))

    @property
    def total_fat(self) -> Decimal:
        return sum((d.fat for d in self.days), Decimal("0"))

    @property
    def has_any_unaccounted(self) -> bool:
        return any(d.unaccounted_entries for d in self.days)


class CycleMacroService:
    def __init__(self, calorie_calc: RecipeCalorieCalculator):
        self.calorie_calc = calorie_calc

    def summarize(self,
                  start: date,
                  end: date,
                  entries: List[MealPlanEntry],
                  recipes_by_id: Dict[str, Recipe]) -> CycleMacroSummary:
        """Roll plan entries into per-day calorie + macro totals.

        Recipes are looked up by id from `recipes_by_id`. Per-serving
        macros come from `RecipeCalorieCalculator` so the math is the
        same as everywhere else in the app. Calories fall back to the
        entry's stored figure when the recipe has zero catalog-backed
        ingredients (legacy seed recipes).
        """
        days = _days_in_range(start, end)
        per_day: Dict[date, DayMacros] = {d: DayMacros(day=d) for d in days}

        # Cache breakdowns per recipe — multiple slots may reference the same one.
        breakdowns: Dict[str, _RecipeMacros] = {}

        for entry in entries:
            if entry.planned_date not in per_day:
                continue  # outside the requested window
            day_macros = per_day[entry.planned_date]
            servings = entry.planned_servings

            recipe = recipes_by_id.get(entry.recipe_id)
            if recipe is None:
                # Recipe was deleted but plan entry remains — best-effort:
                # use the entry's joined calorie figure, leave macros at 0.
                day_macros.calories += servings * (entry.calories_per_serving or 0)
                day_macros.unaccounted_entries += 1
                continue

            macros = breakdowns.get(entry.recipe_id)
            if macros is None:
                macros = _compute_per_serving(self.calorie_calc, recipe, entry)
                breakdowns[entry.recipe_id] = macros

            day_macros.calories += servings * macros.calories
            day_macros.protein += servings * macros.protein
            day_macros.carbs += servings * macros.carbs
            day_macros.fat += servings * macros.fat
            if macros.unaccounted:
                day_macros.unaccounted_entries += 1

        return CycleMacroSummary(days=[per_day[d] for d in days])


@dataclass
class _RecipeMacros:
    calories: int
    protein: Decimal
    carbs: Decimal
    fat: Decimal
    unaccounted: bool


def _compute_per_serving(calc: RecipeCalorieCalculator,
                         recipe: Recipe,
                         entry: MealPlanEntry) -> _RecipeMacros:
    """Per-serving cal+macros for one recipe. Falls back to the entry's
    stored calorie figure when the recipe has no catalog-backed lines."""
    breakdown = calc.compute(recipe)
    if breakdown.lines:
        return _RecipeMacros(
            calories=breakdown.calories_per_serving,
            protein=breakdown.protein_per_serving,
            carbs=breakdown.carbs_per_serving,
            fat=breakdown.fat_per_serving,
            unaccounted=breakdown.unaccounted_count > 0,
        )
    return _RecipeMacros(
        calories=entry.calories_per_serving or 0,
        protein=Decimal("0"),
        carbs=Decimal("0"),
        fat=Decimal("0"),
        unaccounted=True,
    )


def _days_in_range(start: date, end: date) -> List[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]
