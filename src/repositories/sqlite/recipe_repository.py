"""
SQLite implementation of Recipe Repository.

Recipes are owned by a household (per migration 003), with `created_by_user_id`
recording the household member who added them. Ingredient nutrition lives in
the `ingredients` catalog (per migration 005); recipes link to it through the
`recipe_ingredients` join table.
"""
import uuid
from decimal import Decimal
from typing import List, Optional

from core.interfaces.recipe_repository import IRecipeRepository
from core.domain.models import Recipe, Ingredient
from repositories.sqlite.database import DatabaseManager


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

            # Upsert each ingredient into the catalog (zero nutrition for unknown ones).
            ingredient_ids = []
            for ingredient in recipe.ingredients:
                row = cursor.execute(
                    "SELECT id FROM ingredients WHERE name = ?",
                    (ingredient.name,),
                ).fetchone()
                if row:
                    ingredient_id = row['id']
                else:
                    ingredient_id = str(uuid.uuid4())
                    cursor.execute(
                        """
                        INSERT INTO ingredients (id, name, calories_per_100g,
                                                 protein_per_100g, carbs_per_100g, fat_per_100g)
                        VALUES (?, ?, 0, 0, 0, 0)
                        """,
                        (ingredient_id, ingredient.name),
                    )
                ingredient_ids.append((ingredient_id, ingredient))

            cursor.execute(
                """
                INSERT INTO recipes (id, household_id, name, base_servings,
                                     calories_per_serving, created_by_user_id, instructions)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (recipe_id, household_id, recipe.name, recipe.base_servings,
                 recipe.calories_per_serving, created_by_user_id, ""),
            )

            for ingredient_id, ingredient in ingredient_ids:
                cursor.execute(
                    """
                    INSERT INTO recipe_ingredients (id, recipe_id, ingredient_id, quantity, unit)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (str(uuid.uuid4()), recipe_id, ingredient_id,
                     float(ingredient.quantity), ingredient.unit),
                )

            conn.commit()

        return Recipe(
            name=recipe.name,
            ingredients=recipe.ingredients,
            base_servings=recipe.base_servings,
            calories_per_serving=recipe.calories_per_serving,
            id=recipe_id,
        )

    def find_by_id(self, recipe_id: str, household_id: str) -> Optional[Recipe]:
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            recipe_row = cursor.execute(
                """
                SELECT id, name, base_servings, calories_per_serving
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
                SELECT id, name, base_servings, calories_per_serving
                FROM recipes
                WHERE household_id = ?
                ORDER BY created_at DESC
                """,
                (household_id,),
            )
            recipe_rows = cursor.fetchall()
            return [self._build_recipe(cursor, row) for row in recipe_rows]

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
                SELECT id, name, base_servings, calories_per_serving
                FROM recipes
                WHERE name = ? AND household_id = ?
                """,
                (name, household_id),
            ).fetchone()
            if not row:
                return None
            return self._build_recipe(cursor, row)

    def _build_recipe(self, cursor, recipe_row) -> Recipe:
        cursor.execute(
            """
            SELECT i.name, ri.quantity, ri.unit
            FROM recipe_ingredients ri
            JOIN ingredients i ON ri.ingredient_id = i.id
            WHERE ri.recipe_id = ?
            """,
            (recipe_row['id'],),
        )
        ingredients = [
            Ingredient(
                name=ing['name'],
                quantity=Decimal(str(ing['quantity'])),
                unit=ing['unit'],
            )
            for ing in cursor.fetchall()
        ]
        return Recipe(
            name=recipe_row['name'],
            ingredients=ingredients,
            base_servings=recipe_row['base_servings'],
            calories_per_serving=recipe_row['calories_per_serving'],
            id=recipe_row['id'],
        )
