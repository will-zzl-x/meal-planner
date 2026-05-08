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
    CalorieBankingService,
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
