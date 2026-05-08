"""
SQLite implementation of Recipe Repository.
Handles recipes with ingredients and nutritional calculations.
"""
import sqlite3
import uuid
from typing import List, Optional
from decimal import Decimal

from core.interfaces.recipe_repository import IRecipeRepository
from core.domain.models import Recipe, Ingredient
from repositories.database_manager import DatabaseManager

class SQLiteRecipeRepository(IRecipeRepository):
    """SQLite implementation of recipe data access."""
    
    def __init__(self, db_path: str = "meal_planner.db"):
        self.db_manager = DatabaseManager(db_path)
        
        # Initialize database if it doesn't exist
        if not self.db_manager.check_database_exists():
            self.db_manager.initialize_database()
    
    def save(self, recipe: Recipe, user_id: str) -> Recipe:
        """Save a recipe with its ingredients."""
        recipe_id = str(uuid.uuid4())
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Calculate nutrition from ingredients
            total_calories = 0
            total_protein = Decimal('0')
            total_carbs = Decimal('0')
            total_fat = Decimal('0')
            
            # First, save/get ingredients and calculate nutrition
            ingredient_ids = []
            for ingredient in recipe.ingredients:
                # Get or create ingredient in base ingredients table
                cursor.execute("SELECT id FROM ingredients WHERE name = ?", (ingredient.name,))
                row = cursor.fetchone()
                
                if row:
                    ingredient_id = row['id']
                else:
                    # Create new ingredient with default nutrition (to be updated later)
                    ingredient_id = str(uuid.uuid4())
                    cursor.execute("""
                        INSERT INTO ingredients (id, name, calories_per_100g, protein_per_100g, carbs_per_100g, fat_per_100g)
                        VALUES (?, ?, 0, 0, 0, 0)
                    """, (ingredient_id, ingredient.name))
                
                ingredient_ids.append((ingredient_id, ingredient))
            
            # Save recipe
            calories_per_serving = int(total_calories / recipe.base_servings) if recipe.base_servings > 0 else 0
            
            cursor.execute("""
                INSERT INTO recipes (id, user_id, name, base_servings, calories_per_serving, instructions)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (recipe_id, user_id, recipe.name, recipe.base_servings, calories_per_serving, ""))
            
            # Save recipe ingredients
            for ingredient_id, ingredient in ingredient_ids:
                cursor.execute("""
                    INSERT INTO recipe_ingredients (id, recipe_id, ingredient_id, quantity, unit)
                    VALUES (?, ?, ?, ?, ?)
                """, (str(uuid.uuid4()), recipe_id, ingredient_id, float(ingredient.quantity), ingredient.unit))
            
            conn.commit()
        
        # Return recipe with generated ID
        return Recipe(
            name=recipe.name,
            ingredients=recipe.ingredients,
            base_servings=recipe.base_servings,
            calories_per_serving=calories_per_serving
        )
    
    def find_by_id(self, recipe_id: str, user_id: str) -> Optional[Recipe]:
        """Find a recipe by ID for a specific user."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get recipe
            cursor.execute("""
                SELECT name, base_servings, calories_per_serving
                FROM recipes 
                WHERE id = ? AND user_id = ?
            """, (recipe_id, user_id))
            
            recipe_row = cursor.fetchone()
            if not recipe_row:
                return None
            
            # Get ingredients
            cursor.execute("""
                SELECT i.name, ri.quantity, ri.unit
                FROM recipe_ingredients ri
                JOIN ingredients i ON ri.ingredient_id = i.id
                WHERE ri.recipe_id = ?
            """, (recipe_id,))
            
            ingredients = []
            for ing_row in cursor.fetchall():
                ingredients.append(Ingredient(
                    name=ing_row['name'],
                    quantity=Decimal(str(ing_row['quantity'])),
                    unit=ing_row['unit']
                ))
            
            return Recipe(
                name=recipe_row['name'],
                ingredients=ingredients,
                base_servings=recipe_row['base_servings'],
                calories_per_serving=recipe_row['calories_per_serving']
            )
    
    def find_all_by_user(self, user_id: str) -> List[Recipe]:
        """Find all recipes for a specific user."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name, base_servings, calories_per_serving
                FROM recipes 
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
            
            recipes = []
            for recipe_row in cursor.fetchall():
                # Get ingredients for this recipe
                cursor.execute("""
                    SELECT i.name, ri.quantity, ri.unit
                    FROM recipe_ingredients ri
                    JOIN ingredients i ON ri.ingredient_id = i.id
                    WHERE ri.recipe_id = ?
                """, (recipe_row['id'],))
                
                ingredients = []
                for ing_row in cursor.fetchall():
                    ingredients.append(Ingredient(
                        name=ing_row['name'],
                        quantity=Decimal(str(ing_row['quantity'])),
                        unit=ing_row['unit']
                    ))
                
                recipes.append(Recipe(
                    name=recipe_row['name'],
                    ingredients=ingredients,
                    base_servings=recipe_row['base_servings'],
                    calories_per_serving=recipe_row['calories_per_serving']
                ))
            
            return recipes
    
    def delete(self, recipe_id: str, user_id: str) -> bool:
        """Delete a recipe for a specific user."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if recipe exists and belongs to user
            cursor.execute("SELECT id FROM recipes WHERE id = ? AND user_id = ?", (recipe_id, user_id))
            if not cursor.fetchone():
                return False
            
            # Delete recipe (CASCADE will handle ingredients)
            cursor.execute("DELETE FROM recipes WHERE id = ? AND user_id = ?", (recipe_id, user_id))
            conn.commit()
            
            return cursor.rowcount > 0
    
    def find_by_name(self, name: str, user_id: str) -> Optional[Recipe]:
        """Find a recipe by name for a specific user."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name, base_servings, calories_per_serving
                FROM recipes 
                WHERE name = ? AND user_id = ?
            """, (name, user_id))
            
            recipe_row = cursor.fetchone()
            if not recipe_row:
                return None
            
            # Get ingredients
            cursor.execute("""
                SELECT i.name, ri.quantity, ri.unit
                FROM recipe_ingredients ri
                JOIN ingredients i ON ri.ingredient_id = i.id
                WHERE ri.recipe_id = ?
            """, (recipe_row['id'],))
            
            ingredients = []
            for ing_row in cursor.fetchall():
                ingredients.append(Ingredient(
                    name=ing_row['name'],
                    quantity=Decimal(str(ing_row['quantity'])),
                    unit=ing_row['unit']
                ))
            
            return Recipe(
                name=recipe_row['name'],
                ingredients=ingredients,
                base_servings=recipe_row['base_servings'],
                calories_per_serving=recipe_row['calories_per_serving']
            )
