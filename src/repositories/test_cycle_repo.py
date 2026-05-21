"""Tests for SQLiteCycleRepository."""
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).parent.parent))

from repositories.sqlite.cycle_repository import SQLiteCycleRepository
from repositories.sqlite.household_repository import SQLiteHouseholdRepository


def _setup(tmp_path):
    db = str(tmp_path / "test.db")
    households = SQLiteHouseholdRepository(db)
    cycles = SQLiteCycleRepository(db)
    h = households.create("Testville")
    return cycles, h.id


def _week(offset=0) -> tuple[date, date]:
    today = date.today() + timedelta(weeks=offset)
    return today, today + timedelta(days=6)


def test_no_active_cycle_initially(tmp_path):
    cycles, h_id = _setup(tmp_path)
    assert cycles.find_active(h_id) is None


def test_create_returns_active_cycle(tmp_path):
    cycles, h_id = _setup(tmp_path)
    start, end = _week()
    c = cycles.create(h_id, start, end)
    assert c.id
    assert c.household_id == h_id
    assert c.start_date == start
    assert c.end_date == end
    assert c.status == "active"


def test_find_active_returns_created_cycle(tmp_path):
    cycles, h_id = _setup(tmp_path)
    start, end = _week()
    created = cycles.create(h_id, start, end)
    found = cycles.find_active(h_id)
    assert found is not None
    assert found.id == created.id


def test_create_new_cycle_archives_previous(tmp_path):
    cycles, h_id = _setup(tmp_path)
    start1, end1 = _week(0)
    start2, end2 = _week(1)

    old = cycles.create(h_id, start1, end1)
    new = cycles.create(h_id, start2, end2)

    active = cycles.find_active(h_id)
    assert active.id == new.id

    all_cycles = cycles.find_all(h_id)
    archived = [c for c in all_cycles if c.id == old.id]
    assert archived[0].status == "archived"


def test_find_all_newest_first(tmp_path):
    cycles, h_id = _setup(tmp_path)
    cycles.create(h_id, *_week(0))
    cycles.create(h_id, *_week(1))
    cycles.create(h_id, *_week(2))

    all_cycles = cycles.find_all(h_id)
    dates = [c.start_date for c in all_cycles]
    assert dates == sorted(dates, reverse=True)


def test_archive_returns_true_for_existing(tmp_path):
    cycles, h_id = _setup(tmp_path)
    c = cycles.create(h_id, *_week())
    assert cycles.archive(c.id, h_id) is True
    assert cycles.find_active(h_id) is None


def test_archive_returns_false_for_unknown(tmp_path):
    cycles, h_id = _setup(tmp_path)
    assert cycles.archive("nonexistent-id", h_id) is False


def test_cycle_label_same_year(tmp_path):
    cycles, h_id = _setup(tmp_path)
    start = date(2026, 5, 21)
    end = date(2026, 5, 27)
    c = cycles.create(h_id, start, end)
    assert c.label == "May 21 – May 27, 2026"


def test_cycle_length_days(tmp_path):
    cycles, h_id = _setup(tmp_path)
    start = date(2026, 5, 21)
    end = date(2026, 5, 27)
    c = cycles.create(h_id, start, end)
    assert c.length_days == 7


def test_create_rejects_end_before_start(tmp_path):
    cycles, h_id = _setup(tmp_path)
    with pytest.raises(ValueError):
        cycles.create(h_id, date(2026, 5, 21), date(2026, 5, 20))


def test_cycles_isolated_by_household(tmp_path):
    db = str(tmp_path / "test.db")
    households = SQLiteHouseholdRepository(db)
    cycles = SQLiteCycleRepository(db)
    h1 = households.create("Smiths")
    h2 = households.create("Joneses")

    cycles.create(h1.id, *_week())
    assert cycles.find_active(h2.id) is None
