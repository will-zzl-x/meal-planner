"""
Focused robustness tests for the most error-prone parts of the core services:
macro math edge cases, calorie banking redistribution, smart inventory expiration
boundaries, and ingredient aggregation across recipes/units.
"""
import sys
from pathlib import Path
from decimal import Decimal
from datetime import date, timedelta

sys.path.append(str(Path(__file__).parent.parent.parent))

from core.services.macro_tracking_service import (
    MacroTrackingService, MacroTargets, MacroIntake,
)
from core.services.flexible_dieting.calorie_banking_service import CalorieBankingService
from core.services.smart_inventory_service import SmartInventoryService, InventoryItem
from core.services.ingredient_aggregator import IngredientAggregator
from core.domain.models import Recipe, Ingredient


# --- Macro tracking --------------------------------------------------------

def test_macro_intake_total_calories_uses_4_4_9_rule():
    intake = MacroIntake(
        protein_g=Decimal('30'),
        carbs_g=Decimal('40'),
        fats_g=Decimal('10'),
    )
    # 30*4 + 40*4 + 10*9 = 120 + 160 + 90 = 370
    assert intake.total_calories == 370


def test_calculate_macro_targets_meets_minimum_protein_for_low_calorie_diet():
    service = MacroTrackingService()
    # 1200 cal at 30% protein = 360 cal = 90g protein.
    # Minimum protein = 200 lb * 0.8 = 160g. Should clamp to 160.
    targets = service.calculate_macro_targets(
        daily_calories=1200, body_weight=Decimal('200'), activity_level="moderate",
    )
    assert targets.protein_g >= 160


def test_calculate_macro_targets_with_custom_ratios():
    service = MacroTrackingService()
    targets = service.calculate_macro_targets(
        daily_calories=2000,
        body_weight=Decimal('150'),
        custom_ratios={"protein": 0.4, "carbs": 0.3, "fats": 0.3},
    )
    assert targets.calories == 2000
    assert targets.protein_g >= 200  # 2000 * 0.4 / 4 = 200


def test_track_daily_progress_clamps_remaining_at_zero_when_over_target():
    service = MacroTrackingService()
    targets = MacroTargets(protein_g=100, carbs_g=200, fats_g=50, calories=1850)

    # Consume 150g protein — exceeds 100g target.
    progress = service.track_daily_progress(
        targets,
        consumed_recipes=[{
            "ingredients": [
                {"name": "x", "amount": 500, "protein_per_100g": 30,
                 "carbs_per_100g": 0, "fats_per_100g": 0},
            ],
        }],
    )
    assert progress.remaining_protein == 0  # clamped, not negative


def test_calculate_recipe_macros_handles_empty_recipe():
    service = MacroTrackingService()
    macros = service.calculate_recipe_macros({"ingredients": []})
    assert macros.protein_g == Decimal('0')
    assert macros.total_calories == 0


# --- Calorie banking -------------------------------------------------------

def test_remaining_status_over_budget_when_already_exceeded():
    service = CalorieBankingService()
    result = service.calculate_remaining_weekly_calories(
        weekly_target=14000, consumed_so_far=[5000, 5000, 5000], days_remaining=4,
    )
    # Consumed 15000 already → -1000 remaining.
    assert result["remaining_total"] == -1000
    assert result["status"] == "over_budget"


def test_remaining_status_very_low_when_remaining_pace_below_1000_per_day():
    service = CalorieBankingService()
    result = service.calculate_remaining_weekly_calories(
        weekly_target=14000, consumed_so_far=[4000, 4000, 4000], days_remaining=4,
    )
    # 14000 - 12000 = 2000 over 4 days = 500/day → very low.
    assert result["status"] == "very_low"


def test_remaining_status_week_complete_when_no_days_left():
    service = CalorieBankingService()
    result = service.calculate_remaining_weekly_calories(
        weekly_target=14000, consumed_so_far=[2000] * 7, days_remaining=0,
    )
    assert result["status"] == "week_complete"


def test_weekly_distribution_does_not_drop_below_minimum():
    """Special-event banking shouldn't push other days under the user's safety floor."""
    service = CalorieBankingService()
    user_weight = Decimal('150')
    minimum_per_day = int(user_weight * service.minimum_calories_per_lb)

    week_start = date.today() - timedelta(days=date.today().weekday())
    distribution = service.create_weekly_distribution(
        weekly_calorie_target=14000,
        user_weight=user_weight,
        special_events={week_start + timedelta(days=4): "wedding"},
    )
    for target in distribution.daily_targets:
        assert target.final_target >= minimum_per_day, (
            f"day {target.date} dropped below minimum: {target.final_target} < {minimum_per_day}"
        )


# --- Smart inventory expiration -------------------------------------------

def _item(name: str, expires_in_days, location="fridge") -> InventoryItem:
    """Build an inventory item with expiration `expires_in_days` from today (None to skip)."""
    exp = date.today() + timedelta(days=expires_in_days) if expires_in_days is not None else None
    return InventoryItem(
        name=name, quantity=Decimal('1'), unit="oz",
        expiration_date=exp, purchase_date=date.today(), location=location,
    )


def test_is_expired_only_when_strictly_past():
    assert _item("a", expires_in_days=-1).is_expired is True
    assert _item("a", expires_in_days=0).is_expired is False  # expires today, not yet expired
    assert _item("a", expires_in_days=1).is_expired is False
    assert _item("a", expires_in_days=None).is_expired is False  # no date → not expired


def test_is_expiring_soon_inclusive_of_today_and_3_days_out():
    assert _item("a", expires_in_days=0).is_expiring_soon is True
    assert _item("a", expires_in_days=3).is_expiring_soon is True
    assert _item("a", expires_in_days=4).is_expiring_soon is False


def test_get_expiring_items_includes_already_expired_and_sorts_by_date():
    service = SmartInventoryService()
    items = [
        _item("milk", expires_in_days=2),
        _item("yogurt", expires_in_days=-1),
        _item("rice", expires_in_days=10),
    ]
    expiring = service.get_expiring_items(items, days_ahead=3)
    names = [i.name for i in expiring]
    assert "rice" not in names
    assert names == ["yogurt", "milk"]  # already-expired first


def test_add_inventory_item_uses_default_shelf_life_when_no_expiration():
    service = SmartInventoryService()
    item = service.add_inventory_item(
        name="Milk", quantity=Decimal('1'), unit="cup",
        purchase_date=date(2026, 1, 1),
    )
    # default shelf life for milk is 7 days → 2026-01-08
    assert item.expiration_date == date(2026, 1, 8)
    assert item.location == "fridge"


def test_add_inventory_item_with_unknown_food_has_no_expiration():
    service = SmartInventoryService()
    item = service.add_inventory_item(
        name="Mystery Sauce", quantity=Decimal('1'), unit="cup",
    )
    assert item.expiration_date is None  # nothing assumed for unknown items
    assert item.location == "pantry"  # default


# --- Ingredient aggregation across recipes/units --------------------------

def test_aggregate_sums_same_ingredient_same_unit_across_recipes():
    aggregator = IngredientAggregator()
    r1 = Recipe(
        name="R1",
        ingredients=[Ingredient("chicken_breast", Decimal('6'), "oz")],
        base_servings=1, calories_per_serving=400,
    )
    r2 = Recipe(
        name="R2",
        ingredients=[Ingredient("chicken_breast", Decimal('4'), "oz")],
        base_servings=1, calories_per_serving=300,
    )
    result = aggregator.aggregate([r1, r2])
    assert result["chicken_breast_oz"] == Decimal('10')


def test_aggregate_keeps_same_ingredient_with_different_units_separate():
    aggregator = IngredientAggregator()
    r1 = Recipe(
        name="R1",
        ingredients=[Ingredient("rice", Decimal('1'), "cup")],
        base_servings=1, calories_per_serving=200,
    )
    r2 = Recipe(
        name="R2",
        ingredients=[Ingredient("rice", Decimal('1'), "lb")],
        base_servings=1, calories_per_serving=130,
    )
    result = aggregator.aggregate([r1, r2])
    # No cross-unit conversion in aggregator; keeps separate keys.
    assert result["rice_cup"] == Decimal('1')
    assert result["rice_lb"] == Decimal('1')


def test_aggregate_applies_scale_factor_per_recipe():
    aggregator = IngredientAggregator()
    recipe = Recipe(
        name="R1",
        ingredients=[Ingredient("chicken_breast", Decimal('6'), "oz")],
        base_servings=1, calories_per_serving=400,
    )
    result = aggregator.aggregate([recipe], scale_factors={"R1": Decimal('2.5')})
    assert result["chicken_breast_oz"] == Decimal('15')  # 6 * 2.5


def test_aggregate_handles_recipe_not_in_scale_factors():
    aggregator = IngredientAggregator()
    recipe = Recipe(
        name="R1",
        ingredients=[Ingredient("chicken_breast", Decimal('6'), "oz")],
        base_servings=1, calories_per_serving=400,
    )
    # Empty scale_factors → recipe defaults to scale 1.
    result = aggregator.aggregate([recipe], scale_factors={})
    assert result["chicken_breast_oz"] == Decimal('6')
