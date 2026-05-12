"""
SQLite implementation of Recipe Repository.

Recipes are owned by a household (per migration 003), with `created_by_user_id`
recording the household member who added them. Ingredient nutrition lives in
the `ingredients` catalog (per migration 005); recipes link to it through the
`recipe_ingredients` join table. Instructions are stored as a JSON array in a
single TEXT column so individual steps can contain any characters.
"""
import json
import uuid
from decimal import Decimal
from typing import List, Optional

from core.interfaces.recipe_repository import IRecipeRepository
from core.domain.models import Recipe, Ingredient
from repositories.sqlite.database import DatabaseManager


def _serialize_instructions(steps: List[str]) -> str:
    return json.dumps(steps or [])


def _deserialize_instructions(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        # Legacy rows wrote an empty string for instructions; treat any
        # non-JSON value as "no steps recorded" rather than crashing.
        return []
    return value if isinstance(value, list) else []


class SQLiteRecipeRepository(IRecipeRepository):
    """SQLite implementation of recipe data access."""

    def __init__(self, db_path: str = "meal_planner.db"):
        self.db_manager = DatabaseManager(db_path)
        self.db_manager.initialize_database()  # idempotent

    def save(self, recipe: Recipe, household_id: str, created_by_user_id: str) -> Recipe:
        """Save a recipe with its ingredients for a household."""
        recipe_id = str(uuid.uuid4())
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()

            ingredient_ids = []
            for ingredient in recipe.ingredients:
                ingredient_id = self._resolve_or_create_ingredient_id(cursor, ingredient)
                ingredient_ids.append((ingredient_id, ingredient))

            cursor.execute(
                """
                INSERT INTO recipes (id, household_id, name, base_servings,
                                     calories_per_serving, created_by_user_id,
                                     instructions, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (recipe_id, household_id, recipe.name, recipe.base_servings,
                 recipe.calories_per_serving, created_by_user_id,
                 _serialize_instructions(recipe.instructions),
                 recipe.notes),
            )

            for ingredient_id, ingredient in ingredient_ids:
                cursor.execute(
                    """
                    INSERT INTO recipe_ingredients
                        (id, recipe_id, ingredient_id, quantity, unit, store, display_name)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (str(uuid.uuid4()), recipe_id, ingredient_id,
                     float(ingredient.quantity), ingredient.unit, ingredient.store,
                     ingredient.name),
                )

            conn.commit()

        return Recipe(
            name=recipe.name,
            ingredients=recipe.ingredients,
            base_servings=recipe.base_servings,
            calories_per_serving=recipe.calories_per_serving,
            id=recipe_id,
            instructions=list(recipe.instructions),
            notes=recipe.notes,
        )

    def find_by_id(self, recipe_id: str, household_id: str) -> Optional[Recipe]:
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            recipe_row = cursor.execute(
                """
                SELECT id, name, base_servings, calories_per_serving,
                       instructions, notes
                FROM recipes
                WHERE id = ? AND household_id = ?
                """,
                (recipe_id, household_id),
            ).fetchone()
            if not recipe_row:
                return None
            return self._build_recipe(cursor, recipe_row)

    def find_all_by_household(self, household_id: str) -> List[Recipe]:
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name, base_servings, calories_per_serving,
                       instructions, notes
                FROM recipes
                WHERE household_id = ?
                ORDER BY created_at DESC
                """,
                (household_id,),
            )
            recipe_rows = cursor.fetchall()
            return [self._build_recipe(cursor, row) for row in recipe_rows]

    def update(self, recipe: Recipe, household_id: str) -> Optional[Recipe]:
        """Update an existing recipe in place, replacing its ingredient list.

        Implementation note: the simplest correct way to update the ingredient
        list is "delete the join rows and re-insert", which we do inside a
        single transaction so a failure halfway through doesn't leave half-
        replaced ingredients.
        """
        if not recipe.id:
            raise ValueError("update() requires recipe.id to be set")

        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            existing = cursor.execute(
                "SELECT id FROM recipes WHERE id = ? AND household_id = ?",
                (recipe.id, household_id),
            ).fetchone()
            if not existing:
                return None

            cursor.execute(
                """
                UPDATE recipes
                SET name = ?,
                    base_servings = ?,
                    calories_per_serving = ?,
                    instructions = ?,
                    notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND household_id = ?
                """,
                (recipe.name, recipe.base_servings, recipe.calories_per_serving,
                 _serialize_instructions(recipe.instructions),
                 recipe.notes, recipe.id, household_id),
            )

            # Replace ingredient associations.
            cursor.execute(
                "DELETE FROM recipe_ingredients WHERE recipe_id = ?",
                (recipe.id,),
            )
            for ingredient in recipe.ingredients:
                ingredient_id = self._resolve_or_create_ingredient_id(cursor, ingredient)
                cursor.execute(
                    """
                    INSERT INTO recipe_ingredients
                        (id, recipe_id, ingredient_id, quantity, unit, store, display_name)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (str(uuid.uuid4()), recipe.id, ingredient_id,
                     float(ingredient.quantity), ingredient.unit, ingredient.store,
                     ingredient.name),
                )

            conn.commit()

        return Recipe(
            name=recipe.name,
            ingredients=list(recipe.ingredients),
            base_servings=recipe.base_servings,
            calories_per_serving=recipe.calories_per_serving,
            id=recipe.id,
            instructions=list(recipe.instructions),
            notes=recipe.notes,
        )

    def delete_by_name(self, name: str, household_id: str) -> bool:
        """Delete a recipe by its name within a household. Convenience for the V1 UI,
        which doesn't surface recipe IDs."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM recipes WHERE name = ? AND household_id = ?",
                (name, household_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete(self, recipe_id: str, household_id: str) -> bool:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(
                "SELECT id FROM recipes WHERE id = ? AND household_id = ?",
                (recipe_id, household_id),
            )
            if not cursor.fetchone():
                return False
            cursor = conn.execute(
                "DELETE FROM recipes WHERE id = ? AND household_id = ?",
                (recipe_id, household_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def find_by_name(self, name: str, household_id: str) -> Optional[Recipe]:
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            row = cursor.execute(
                """
                SELECT id, name, base_servings, calories_per_serving,
                       instructions, notes
                FROM recipes
                WHERE name = ? AND household_id = ?
                """,
                (name, household_id),
            ).fetchone()
            if not row:
                return None
            return self._build_recipe(cursor, row)

    def _resolve_or_create_ingredient_id(self, cursor, ingredient: Ingredient) -> str:
        """Resolve an Ingredient to a row id in the `ingredients` table.

        Three cases, in priority order:
        1. Ingredient.catalog_ingredient_id set — picker-built; use as-is.
           This is the path for ingredients added via the food-search UI:
           the catalog row already exists with real per-serving nutrition.
        2. A row with the same name exists — reuse it (legacy free-text path).
        3. Otherwise insert a stub row with zero nutrition (legacy path,
           used by seed recipes and any caller still building Ingredients
           by hand without a catalog reference).
        """
        if ingredient.catalog_ingredient_id:
            return ingredient.catalog_ingredient_id
        row = cursor.execute(
            "SELECT id FROM ingredients WHERE name = ?",
            (ingredient.name,),
        ).fetchone()
        if row:
            return row['id']
        new_id = str(uuid.uuid4())
        cursor.execute(
            """
            INSERT INTO ingredients (id, name, calories_per_100g,
                                     protein_per_100g, carbs_per_100g, fat_per_100g)
            VALUES (?, ?, 0, 0, 0, 0)
            """,
            (new_id, ingredient.name),
        )
        return new_id

    def _build_recipe(self, cursor, recipe_row) -> Recipe:
        # Pulling catalog source/serving info alongside the join row lets the
        # calorie calculator distinguish picker-backed ingredients (real
        # nutrition) from legacy free-text ones (zero nutrition stubs).
        # `display_name` (migration 010) preserves the user-typed name on
        # the join row so backfilled recipes don't visibly morph into
        # catalog canonical names ("Skinless chicken thighs (~4)" should
        # not become just "Chicken Breast" after a backfill).
        cursor.execute(
            """
            SELECT i.id AS ingredient_id, i.name AS catalog_name, i.source,
                   ri.quantity, ri.unit, ri.store, ri.display_name
            FROM recipe_ingredients ri
            JOIN ingredients i ON ri.ingredient_id = i.id
            WHERE ri.recipe_id = ?
            """,
            (recipe_row['id'],),
        )
        ingredients: List[Ingredient] = []
        for ing in cursor.fetchall():
            qty = Decimal(str(ing['quantity']))
            # Any non-null `source` means the ingredient row carries real
            # per-serving nutrition (USDA / Open Food Facts / sample / manual).
            # Legacy zero-nutrition stubs created before 8a have source = NULL.
            picker_backed = ing['source'] is not None
            display_name = ing['display_name'] or ing['catalog_name']
            ingredients.append(Ingredient(
                name=display_name,
                quantity=qty,
                unit=ing['unit'],
                store=ing['store'],
                catalog_ingredient_id=ing['ingredient_id'] if picker_backed else None,
                servings=qty if picker_backed else None,
            ))
        return Recipe(
            name=recipe_row['name'],
            ingredients=ingredients,
            base_servings=recipe_row['base_servings'],
            calories_per_serving=recipe_row['calories_per_serving'],
            id=recipe_row['id'],
            instructions=_deserialize_instructions(recipe_row['instructions']),
            notes=recipe_row['notes'],
        )
