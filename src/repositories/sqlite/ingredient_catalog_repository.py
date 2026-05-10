"""
SQLite repository for the ingredient catalog — the local cache of items
the user has picked from real food databases (USDA, Open Food Facts) or
entered manually.

Migration 009 widened the existing `ingredients` table with per-serving
nutrition columns plus a (source, external_id) pair. This repo only
touches those new columns; the older per-100g columns remain for
recipe_repository's legacy code path until slice 8b removes it.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import List, Optional

from core.domain.models import CatalogIngredient
from repositories.sqlite.database import DatabaseManager


def _row_to_catalog(row) -> CatalogIngredient:
    return CatalogIngredient(
        id=row["id"],
        name=row["name"],
        serving_label=row["serving_label"] or "100g",
        calories_per_serving=int(row["calories_per_serving"] or 0),
        protein_per_serving=Decimal(str(row["protein_per_serving"] or 0)),
        carbs_per_serving=Decimal(str(row["carbs_per_serving"] or 0)),
        fat_per_serving=Decimal(str(row["fat_per_serving"] or 0)),
        brand=row["brand"],
        source=row["source"],
        external_id=row["external_id"],
    )


class SQLiteIngredientCatalogRepository:
    """Local cache for foods picked from real nutrition databases."""

    def __init__(self, db_path: str = "meal_planner.db"):
        self.db_manager = DatabaseManager(db_path)
        self.db_manager.initialize_database()

    def find_by_external_id(self, source: str, external_id: str) -> Optional[CatalogIngredient]:
        """Return the cached row that came from a particular database row,
        or None if we haven't seen it before."""
        with self.db_manager.get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, name, brand, serving_label,
                       calories_per_serving, protein_per_serving,
                       carbs_per_serving, fat_per_serving,
                       source, external_id
                FROM ingredients
                WHERE source = ? AND external_id = ?
                """,
                (source, external_id),
            ).fetchone()
            return _row_to_catalog(row) if row else None

    def find_by_id(self, ingredient_id: str) -> Optional[CatalogIngredient]:
        with self.db_manager.get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, name, brand, serving_label,
                       calories_per_serving, protein_per_serving,
                       carbs_per_serving, fat_per_serving,
                       source, external_id
                FROM ingredients
                WHERE id = ?
                """,
                (ingredient_id,),
            ).fetchone()
            return _row_to_catalog(row) if row else None

    def save(self, ingredient: CatalogIngredient) -> CatalogIngredient:
        """Insert or update a catalog row.

        Dedup rule: if (source, external_id) already exists we update that
        row in place. Otherwise insert a fresh row with a new UUID. This
        means picking the same USDA item twice doesn't create duplicates.
        """
        if ingredient.source and ingredient.external_id:
            existing = self.find_by_external_id(ingredient.source, ingredient.external_id)
            if existing:
                return self._update(existing.id, ingredient)
        return self._insert(ingredient)

    def _insert(self, ingredient: CatalogIngredient) -> CatalogIngredient:
        new_id = ingredient.id or str(uuid.uuid4())
        # `name` is UNIQUE on the legacy ingredients table. If the user
        # picks two foods with the same display description, disambiguate
        # by appending the external id.
        unique_name = self._unique_name(ingredient.name, ingredient.external_id)
        with self.db_manager.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO ingredients
                    (id, name, brand, serving_label,
                     calories_per_serving, protein_per_serving,
                     carbs_per_serving, fat_per_serving,
                     source, external_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (new_id, unique_name, ingredient.brand, ingredient.serving_label,
                 ingredient.calories_per_serving,
                 float(ingredient.protein_per_serving),
                 float(ingredient.carbs_per_serving),
                 float(ingredient.fat_per_serving),
                 ingredient.source, ingredient.external_id),
            )
            conn.commit()
        return CatalogIngredient(
            id=new_id,
            name=unique_name,
            serving_label=ingredient.serving_label,
            calories_per_serving=ingredient.calories_per_serving,
            protein_per_serving=ingredient.protein_per_serving,
            carbs_per_serving=ingredient.carbs_per_serving,
            fat_per_serving=ingredient.fat_per_serving,
            brand=ingredient.brand,
            source=ingredient.source,
            external_id=ingredient.external_id,
        )

    def _update(self, existing_id: str, ingredient: CatalogIngredient) -> CatalogIngredient:
        with self.db_manager.get_connection() as conn:
            conn.execute(
                """
                UPDATE ingredients
                SET brand = ?,
                    serving_label = ?,
                    calories_per_serving = ?,
                    protein_per_serving = ?,
                    carbs_per_serving = ?,
                    fat_per_serving = ?
                WHERE id = ?
                """,
                (ingredient.brand, ingredient.serving_label,
                 ingredient.calories_per_serving,
                 float(ingredient.protein_per_serving),
                 float(ingredient.carbs_per_serving),
                 float(ingredient.fat_per_serving),
                 existing_id),
            )
            conn.commit()
        loaded = self.find_by_id(existing_id)
        assert loaded is not None
        return loaded

    def search_by_name(self, query: str, limit: int = 20) -> List[CatalogIngredient]:
        """Substring search across cached items. Used so picks the user has
        already cached show up first in the UI."""
        with self.db_manager.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, name, brand, serving_label,
                       calories_per_serving, protein_per_serving,
                       carbs_per_serving, fat_per_serving,
                       source, external_id
                FROM ingredients
                WHERE calories_per_serving IS NOT NULL
                  AND (name LIKE ? OR brand LIKE ?)
                ORDER BY name
                LIMIT ?
                """,
                (f"%{query}%", f"%{query}%", limit),
            ).fetchall()
            return [_row_to_catalog(r) for r in rows]

    def _unique_name(self, name: str, external_id: Optional[str]) -> str:
        with self.db_manager.get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM ingredients WHERE name = ? LIMIT 1",
                (name,),
            ).fetchone()
            if not row:
                return name
        # Conflict — disambiguate. Use external_id if available, else uuid suffix.
        suffix = external_id or str(uuid.uuid4())[:8]
        return f"{name} ({suffix})"
