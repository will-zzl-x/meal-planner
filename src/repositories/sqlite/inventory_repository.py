"""
SQLite implementation of Inventory Repository.

Inventory rows are scoped to a household (per migration 002). Each
(household_id, ingredient_name, unit) is unique, so adding the "same" item
twice updates the existing row's quantity rather than creating a duplicate.

Note: the V1 schema only persists name + quantity + unit. The optional
`expiration_date`, `purchase_date`, and `location` fields on the domain
InventoryItem are not stored yet — they round-trip as None / defaults.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from core.domain.models import InventoryItem
from core.interfaces.inventory_repository import IInventoryRepository
from repositories.sqlite.database import DatabaseManager


class SQLiteInventoryRepository(IInventoryRepository):
    """SQLite implementation of household inventory data access."""

    def __init__(self, db_path: str = "meal_planner.db"):
        self.db_manager = DatabaseManager(db_path)
        self.db_manager.initialize_database()  # idempotent

    def get_household_inventory(self, household_id: str) -> List[InventoryItem]:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT ingredient_name, quantity, unit, catalog_ingredient_id
                FROM inventory
                WHERE household_id = ?
                ORDER BY ingredient_name
                """,
                (household_id,),
            )
            return [
                InventoryItem(
                    name=row['ingredient_name'],
                    quantity=Decimal(str(row['quantity'])),
                    unit=row['unit'],
                    catalog_ingredient_id=row['catalog_ingredient_id'],
                )
                for row in cursor.fetchall()
            ]

    def update_household_inventory(self, household_id: str,
                                   items: List[InventoryItem]) -> None:
        """Replace the household's full inventory in a single transaction."""
        with self.db_manager.get_connection() as conn:
            conn.execute("DELETE FROM inventory WHERE household_id = ?", (household_id,))
            for item in items:
                conn.execute(
                    """
                    INSERT INTO inventory
                        (id, household_id, ingredient_name, quantity, unit, catalog_ingredient_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (str(uuid.uuid4()), household_id, item.name,
                     float(item.quantity), item.unit, item.catalog_ingredient_id),
                )
            conn.commit()

    def add_inventory_item(self, household_id: str,
                           item: InventoryItem) -> InventoryItem:
        """Insert the item, or replace the quantity if (name, unit) already exists.

        On replace, also overwrite the catalog_ingredient_id — letting a
        user "link" an existing free-text pantry row to a catalog entry
        by adding it again with the link.
        """
        with self.db_manager.get_connection() as conn:
            existing = conn.execute(
                """
                SELECT id FROM inventory
                WHERE household_id = ? AND ingredient_name = ? AND unit = ?
                """,
                (household_id, item.name, item.unit),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE inventory
                    SET quantity = ?,
                        catalog_ingredient_id = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (float(item.quantity), item.catalog_ingredient_id, existing['id']),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO inventory
                        (id, household_id, ingredient_name, quantity, unit, catalog_ingredient_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (str(uuid.uuid4()), household_id, item.name,
                     float(item.quantity), item.unit, item.catalog_ingredient_id),
                )
            conn.commit()
        return item

    def remove_inventory_item(self, household_id: str,
                              ingredient_name: str, unit: str) -> bool:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(
                """
                DELETE FROM inventory
                WHERE household_id = ? AND ingredient_name = ? AND unit = ?
                """,
                (household_id, ingredient_name, unit),
            )
            conn.commit()
            return cursor.rowcount > 0

    def clear_household_inventory(self, household_id: str) -> None:
        with self.db_manager.get_connection() as conn:
            conn.execute("DELETE FROM inventory WHERE household_id = ?", (household_id,))
            conn.commit()

    def last_reviewed_at(self, household_id: str) -> Optional[datetime]:
        """Return the most recent updated_at across the household's
        inventory rows — used as a "last pantry check-in" timestamp.
        Returns None for an empty pantry (or one we've never touched)."""
        with self.db_manager.get_connection() as conn:
            row = conn.execute(
                """
                SELECT MAX(updated_at) AS last
                FROM inventory
                WHERE household_id = ?
                """,
                (household_id,),
            ).fetchone()
        if not row or not row['last']:
            return None
        try:
            return datetime.fromisoformat(row['last'])
        except (ValueError, TypeError):
            return None
