"""Tests for SQLiteInventoryRepository (migration 002)."""
import sys
from decimal import Decimal
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from core.domain.models import InventoryItem
from repositories.sqlite.household_repository import SQLiteHouseholdRepository
from repositories.sqlite.inventory_repository import SQLiteInventoryRepository


def _setup(tmp_path):
    db = str(tmp_path / "inv.db")
    households = SQLiteHouseholdRepository(db)
    inv = SQLiteInventoryRepository(db)
    h1 = households.create("Smiths")
    h2 = households.create("Joneses")
    return inv, h1, h2


def _item(name="rice", qty="2", unit="cup") -> InventoryItem:
    return InventoryItem(name=name, quantity=Decimal(qty), unit=unit)


def test_add_and_list(tmp_path):
    inv, h1, _ = _setup(tmp_path)
    inv.add_inventory_item(h1.id, _item())
    inv.add_inventory_item(h1.id, _item("oats", "1.5", "lb"))
    items = inv.get_household_inventory(h1.id)
    assert {i.name for i in items} == {"rice", "oats"}


def test_add_with_existing_name_and_unit_replaces_quantity(tmp_path):
    inv, h1, _ = _setup(tmp_path)
    inv.add_inventory_item(h1.id, _item("rice", "2", "cup"))
    inv.add_inventory_item(h1.id, _item("rice", "5", "cup"))  # same key
    items = inv.get_household_inventory(h1.id)
    assert len(items) == 1
    assert items[0].quantity == Decimal("5")


def test_same_name_different_unit_keeps_separate_rows(tmp_path):
    inv, h1, _ = _setup(tmp_path)
    inv.add_inventory_item(h1.id, _item("rice", "2", "cup"))
    inv.add_inventory_item(h1.id, _item("rice", "1", "lb"))
    assert len(inv.get_household_inventory(h1.id)) == 2


def test_household_isolation(tmp_path):
    inv, h1, h2 = _setup(tmp_path)
    inv.add_inventory_item(h1.id, _item("rice", "2", "cup"))
    assert inv.get_household_inventory(h2.id) == []


def test_remove_inventory_item(tmp_path):
    inv, h1, _ = _setup(tmp_path)
    inv.add_inventory_item(h1.id, _item("rice", "2", "cup"))
    assert inv.remove_inventory_item(h1.id, "rice", "cup") is True
    assert inv.remove_inventory_item(h1.id, "rice", "cup") is False
    assert inv.get_household_inventory(h1.id) == []


def test_clear_inventory(tmp_path):
    inv, h1, h2 = _setup(tmp_path)
    inv.add_inventory_item(h1.id, _item("rice", "2", "cup"))
    inv.add_inventory_item(h2.id, _item("oats", "1", "lb"))
    inv.clear_household_inventory(h1.id)
    assert inv.get_household_inventory(h1.id) == []
    # Other household untouched.
    assert len(inv.get_household_inventory(h2.id)) == 1


def test_update_household_inventory_replaces_atomically(tmp_path):
    inv, h1, _ = _setup(tmp_path)
    inv.add_inventory_item(h1.id, _item("rice", "2", "cup"))
    inv.update_household_inventory(h1.id, [
        _item("oats", "1", "lb"),
        _item("milk", "1", "cup"),  # cup unit is allowed by validator
    ])
    items = inv.get_household_inventory(h1.id)
    assert {i.name for i in items} == {"oats", "milk"}
