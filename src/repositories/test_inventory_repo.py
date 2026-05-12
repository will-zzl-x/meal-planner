"""Tests for SQLiteInventoryRepository against the household-scoped inventory table."""
import sys
from decimal import Decimal
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from core.domain.models import InventoryItem
from repositories.sqlite.household_repository import SQLiteHouseholdRepository
from repositories.sqlite.inventory_repository import SQLiteInventoryRepository


def _setup(tmp_path):
    db_path = str(tmp_path / "test.db")
    households = SQLiteHouseholdRepository(db_path)
    inventory = SQLiteInventoryRepository(db_path)
    return households, inventory


def test_empty_inventory_for_new_household(tmp_path):
    households, inventory = _setup(tmp_path)
    h = households.create("Smiths")
    assert inventory.get_household_inventory(h.id) == []


def test_add_and_list_inventory_items(tmp_path):
    households, inventory = _setup(tmp_path)
    h = households.create("Smiths")
    inventory.add_inventory_item(h.id, InventoryItem(name="rice", quantity=Decimal("2"), unit="lb"))
    inventory.add_inventory_item(h.id, InventoryItem(name="milk", quantity=Decimal("1"), unit="cup"))

    items = inventory.get_household_inventory(h.id)
    assert {(i.name, i.unit) for i in items} == {("rice", "lb"), ("milk", "cup")}


def test_adding_same_name_unit_replaces_quantity(tmp_path):
    households, inventory = _setup(tmp_path)
    h = households.create("Smiths")
    inventory.add_inventory_item(h.id, InventoryItem(name="rice", quantity=Decimal("2"), unit="lb"))
    inventory.add_inventory_item(h.id, InventoryItem(name="rice", quantity=Decimal("5"), unit="lb"))

    items = inventory.get_household_inventory(h.id)
    assert len(items) == 1
    assert items[0].quantity == Decimal("5")


def test_remove_inventory_item(tmp_path):
    households, inventory = _setup(tmp_path)
    h = households.create("Smiths")
    inventory.add_inventory_item(h.id, InventoryItem(name="rice", quantity=Decimal("2"), unit="lb"))

    assert inventory.remove_inventory_item(h.id, "rice", "lb") is True
    assert inventory.get_household_inventory(h.id) == []
    # Removing something that isn't there is a no-op, returns False.
    assert inventory.remove_inventory_item(h.id, "rice", "lb") is False


def test_inventory_isolated_per_household(tmp_path):
    households, inventory = _setup(tmp_path)
    h1 = households.create("Smiths")
    h2 = households.create("Joneses")
    inventory.add_inventory_item(h1.id, InventoryItem(name="rice", quantity=Decimal("2"), unit="lb"))
    inventory.add_inventory_item(h2.id, InventoryItem(name="milk", quantity=Decimal("1"), unit="cup"))

    smith = inventory.get_household_inventory(h1.id)
    jones = inventory.get_household_inventory(h2.id)
    assert {i.name for i in smith} == {"rice"}
    assert {i.name for i in jones} == {"milk"}


def test_clear_household_inventory(tmp_path):
    households, inventory = _setup(tmp_path)
    h = households.create("Smiths")
    inventory.add_inventory_item(h.id, InventoryItem(name="rice", quantity=Decimal("2"), unit="lb"))
    inventory.add_inventory_item(h.id, InventoryItem(name="milk", quantity=Decimal("1"), unit="cup"))

    inventory.clear_household_inventory(h.id)
    assert inventory.get_household_inventory(h.id) == []


def test_update_household_inventory_replaces_full_set(tmp_path):
    households, inventory = _setup(tmp_path)
    h = households.create("Smiths")
    inventory.add_inventory_item(h.id, InventoryItem(name="rice", quantity=Decimal("2"), unit="lb"))

    inventory.update_household_inventory(h.id, [
        InventoryItem(name="oats", quantity=Decimal("3"), unit="cup"),
    ])
    items = inventory.get_household_inventory(h.id)
    assert {i.name for i in items} == {"oats"}
