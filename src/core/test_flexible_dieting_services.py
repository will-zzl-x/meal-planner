"""
Tests for the flexible-dieting business-logic services:
WeightTrackingService, CalorieBankingService, BodyCompositionService.
"""
import sys
from pathlib import Path
from decimal import Decimal
from datetime import date, timedelta

sys.path.append(str(Path(__file__).parent.parent))

from core.services.flexible_dieting import (
    WeightTrackingService, WeightLog,
    CalorieBankingService, DailyCalorieTarget, WeeklyDistribution,
    BodyCompositionService,
)


# --- WeightTrackingService -------------------------------------------------

def _build_logs(start_weight: Decimal, days: int, daily_loss: Decimal) -> list:
    """Build date-desc logs simulating weight loss: oldest entries are heavier."""
    return [
        WeightLog(
            user_id="u",
            date=date.today() - timedelta(days=i),
            weight=start_weight + (i * daily_loss),  # i days ago, user weighed more
            notes=f"day {i}",
        )
        for i in range(days)
    ]


def test_weekly_average_change_returns_zero_for_flat_weight():
    service = WeightTrackingService()
    logs = _build_logs(Decimal('180'), days=14, daily_loss=Decimal('0'))
    assert service.calculate_weekly_average_change(logs) == Decimal('0')


def test_weekly_average_change_is_negative_for_consistent_loss():
    service = WeightTrackingService()
    # 0.143 lb/day ≈ 1 lb/week loss
    logs = _build_logs(Decimal('180'), days=28, daily_loss=Decimal('0.143'))
    weekly = service.calculate_weekly_average_change(logs)
    assert weekly < 0
    assert abs(weekly + Decimal('1')) < Decimal('0.5')  # within ~0.5 lb of -1


def test_analyze_weight_progress_reports_current_weight():
    service = WeightTrackingService()
    logs = _build_logs(Decimal('180'), days=14, daily_loss=Decimal('0.1'))
    progress = service.analyze_weight_progress(logs)
    # Most recent log (day 0) is at the start_weight in our builder.
    assert progress.current_weight == Decimal('180')


def test_estimate_tdee_runs_for_typical_inputs():
    service = WeightTrackingService()
    logs = _build_logs(Decimal('180'), days=28, daily_loss=Decimal('0.143'))

    class _Log:
        def __init__(self, c):
            self.consumed_calories = c

    calorie_logs = [_Log(1800) for _ in range(28)]
    tdee = service.estimate_tdee(logs, calorie_logs, Decimal('180'))

    # If you're losing weight while eating 1800, TDEE must be > 1800.
    assert tdee.estimated_tdee > 1800
    assert tdee.recommended_daily_calories > 0


# --- CalorieBankingService -------------------------------------------------

def test_create_weekly_distribution_sums_to_total():
    service = CalorieBankingService()
    weekly_target = 14000
    distribution = service.create_weekly_distribution(
        weekly_target, Decimal('180'), special_events={}
    )
    total = sum(t.final_target for t in distribution.daily_targets)
    assert total == weekly_target
    assert len(distribution.daily_targets) == 7


def test_create_weekly_distribution_marks_special_event_day():
    service = CalorieBankingService()
    # The planning week starts on Monday; pick an event day that's definitely in it.
    week_start = date.today() - timedelta(days=date.today().weekday())
    event_date = week_start + timedelta(days=4)  # Friday of the current week
    distribution = service.create_weekly_distribution(
        14000, Decimal('180'), special_events={event_date: "wedding"}
    )
    special = [t for t in distribution.daily_targets if t.is_special_event]
    assert len(special) == 1
    assert special[0].date == event_date
    # Special event days should have a higher allowance than the average baseline.
    avg = 14000 // 7
    assert special[0].final_target > avg


def test_remaining_calories_calculation():
    service = CalorieBankingService()
    # 3 days: consumed 2000, 1800, 2200 = 6000 of 14000 weekly. 4 days left.
    result = service.calculate_remaining_weekly_calories(
        weekly_target=14000, consumed_so_far=[2000, 1800, 2200], days_remaining=4
    )
    assert result["remaining_total"] == 8000
    assert result["daily_average"] == 2000


def test_distribute_weekly_calories_basic_split_within_minimums():
    service = CalorieBankingService()
    week_start = date.today() - timedelta(days=date.today().weekday())
    distribution = service.distribute_weekly_calories(
        weekly_target=14000,
        body_weight=Decimal("180"),
        week_start_date=week_start,
    )
    assert len(distribution.daily_targets) == 7
    # Legacy alias still works for callers that read .target_calories.
    assert all(t.target_calories == t.final_target for t in distribution.daily_targets)
    # No special days so no day should fall below the per-pound minimum.
    minimum = int(Decimal("180") * service.minimum_calories_per_lb)
    assert all(t.final_target >= minimum for t in distribution.daily_targets)


def test_distribute_weekly_calories_marks_restaurant_day():
    service = CalorieBankingService()
    week_start = date.today() - timedelta(days=date.today().weekday())
    friday = week_start + timedelta(days=4)
    distribution = service.distribute_weekly_calories(
        weekly_target=14000,
        body_weight=Decimal("180"),
        week_start_date=week_start,
        special_days={friday: "restaurant"},
    )
    friday_target = next(t for t in distribution.daily_targets if t.date == friday)
    assert friday_target.is_special_event
    # Restaurant day should sit above the simple 14000/7 = 2000 average.
    assert friday_target.final_target > 2000


def test_calculate_banking_impact_under_and_over():
    service = CalorieBankingService()
    new_banked, msg = service.calculate_banking_impact(1800, 2000, 0)
    assert new_banked == 200
    assert "Banked" in msg

    new_banked, msg = service.calculate_banking_impact(2300, 2000, 200)
    assert new_banked == -100
    assert "Used" in msg


def test_redistribute_for_special_day_pulls_from_other_days():
    service = CalorieBankingService()
    week_start = date.today() - timedelta(days=date.today().weekday())
    distribution = service.distribute_weekly_calories(
        weekly_target=14000,
        body_weight=Decimal("180"),
        week_start_date=week_start,
    )
    friday = week_start + timedelta(days=4)
    redistributed = service.redistribute_for_special_day(
        current_distribution=distribution,
        special_date=friday,
        estimated_calories=2800,
        body_weight=Decimal("180"),
    )
    friday_target = next(t for t in redistributed.daily_targets if t.date == friday)
    assert friday_target.final_target == 2800
    other_totals = [t.final_target for t in redistributed.daily_targets if t.date != friday]
    # Other days got reduced from their original ~2000 baseline.
    assert max(other_totals) < 2000


def test_validate_distribution_safety_flags_low_days():
    service = CalorieBankingService()
    week_start = date.today() - timedelta(days=date.today().weekday())
    unsafe = WeeklyDistribution(
        week_start_date=week_start,
        total_weekly_calories=8400,
        daily_targets=[
            DailyCalorieTarget(
                date=week_start + timedelta(days=i),
                base_target=1200, banked_calories=0, borrowed_calories=0,
                final_target=1200,
            )
            for i in range(7)
        ],
        total_banked=0,
        total_borrowed=0,
        is_balanced=True,
    )
    warnings = service.validate_distribution_safety(unsafe, Decimal("180"))
    assert len(warnings) >= 1


# --- BodyCompositionService ------------------------------------------------

def test_lean_body_mass_matches_formula():
    service = BodyCompositionService()
    weight = Decimal('200')
    bf_pct = Decimal('20')
    lean = service.estimate_lean_body_mass(weight, bf_pct)
    # Lean = total * (1 - bf%/100) = 200 * 0.8 = 160
    assert lean == Decimal('160')


def test_goal_weight_preserves_lean_mass():
    service = BodyCompositionService()
    current_weight = Decimal('200')
    current_bf = Decimal('20')   # → 160 lb lean
    target_bf = Decimal('15')    # → goal_weight = 160 / (1 - 0.15) ≈ 188.235

    goal = service.calculate_goal_weight(current_weight, current_bf, target_bf)
    expected = Decimal('160') / Decimal('0.85')
    assert abs(goal - expected) < Decimal('0.5')


def test_body_fat_references_returned():
    service = BodyCompositionService()
    refs = service.get_body_fat_references()
    assert len(refs) > 0
    assert all(hasattr(r, 'percentage') for r in refs)


def test_assess_body_composition_returns_safe_target():
    service = BodyCompositionService()
    result = service.assess_body_composition(
        body_fat_percentage=Decimal("15"),
        current_weight=Decimal("180"),
        activity_level="moderate",
    )
    # Must respect 10 cal/lb floor and produce a self-consistent weekly total.
    assert result.daily_calorie_target >= int(Decimal("180") * 10)
    assert result.weekly_calorie_target == result.daily_calorie_target * 7
    assert result.assessment_category in BodyCompositionService.BF_CATEGORIES


def test_assess_body_composition_responds_to_activity_level():
    service = BodyCompositionService()
    sedentary = service.assess_body_composition(Decimal("20"), Decimal("170"), "sedentary")
    very_active = service.assess_body_composition(Decimal("20"), Decimal("170"), "very_active")
    # Higher activity → higher TDEE → higher target (deficit is held constant by category).
    assert very_active.daily_calorie_target > sedentary.daily_calorie_target


def test_get_photo_reference_ranges_keys():
    service = BodyCompositionService()
    ranges = service.get_photo_reference_ranges()
    assert set(ranges.keys()) == {"very_lean", "lean", "average", "soft", "high"}


def test_validate_calorie_target_floor_and_ceiling():
    service = BodyCompositionService()
    ok, _ = service.validate_calorie_target(2000, Decimal("180"))
    assert ok is True

    too_low, msg = service.validate_calorie_target(1200, Decimal("180"))
    assert too_low is False
    assert "Minimum" in msg

    too_high, msg = service.validate_calorie_target(5000, Decimal("180"))
    assert too_high is False
