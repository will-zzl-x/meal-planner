#!/usr/bin/env python3
"""
Test Recipe Repository functionality.
"""
import sqlite3
import uuid
from decimal import Decimal
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class Ingredient:
    name: str
    quantity: Decimal
    unit: str

@dataclass  
class Recipe:
    name: str
    ingredients: List[Ingredient]
    base_servings: int
    calories_per_serving: int

class SimpleRecipeRepository:
    """Simple recipe repository for testing."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL
                );
                
                CREATE TABLE IF NOT EXISTS ingredients (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    calories_per_100g INTEGER DEFAULT 0
                );
                
                CREATE TABLE IF NOT EXISTS recipes (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    base_servings INTEGER NOT NULL,
                    calories_per_serving INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
                
                CREATE TABLE IF NOT EXISTS recipe_ingredients (
                    id TEXT PRIMARY KEY,
                    recipe_id TEXT NOT NULL,
                    ingredient_id TEXT NOT NULL,
                    quantity DECIMAL(10,2) NOT NULL,
                    unit TEXT NOT NULL,
                    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
                    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id)
                );
            """)
    
    def save_recipe(self, recipe: Recipe, user_id: str) -> str:
        """Save a recipe and return its ID."""
        recipe_id = str(uuid.uuid4())
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Save recipe
            cursor.execute("""
                INSERT INTO recipes (id, user_id, name, base_servings, calories_per_serving)
                VALUES (?, ?, ?, ?, ?)
            """, (recipe_id, user_id, recipe.name, recipe.base_servings, recipe.calories_per_serving))
            
            # Save ingredients
            for ingredient in recipe.ingredients:
                # Get or create ingredient
                cursor.execute("SELECT id FROM ingredients WHERE name = ?", (ingredient.name,))
                row = cursor.fetchone()
                
                if row:
                    ingredient_id = row['id']
                else:
                    ingredient_id = str(uuid.uuid4())
                    cursor.execute("INSERT INTO ingredients (id, name) VALUES (?, ?)", 
                                 (ingredient_id, ingredient.name))
                
                # Link ingredient to recipe
                cursor.execute("""
                    INSERT INTO recipe_ingredients (id, recipe_id, ingredient_id, quantity, unit)
                    VALUES (?, ?, ?, ?, ?)
                """, (str(uuid.uuid4()), recipe_id, ingredient_id, float(ingredient.quantity), ingredient.unit))
            
            conn.commit()
        
        return recipe_id
    
    def find_recipe(self, recipe_id: str, user_id: str) -> Optional[Recipe]:
        """Find recipe by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get recipe
            cursor.execute("""
                SELECT name, base_servings, calories_per_serving
                FROM recipes WHERE id = ? AND user_id = ?
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
    
    def get_user_recipes(self, user_id: str) -> List[Recipe]:
        """Get all recipes for a user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, name, base_servings, calories_per_serving FROM recipes WHERE user_id = ?", 
                         (user_id,))
            
            recipes = []
            for recipe_row in cursor.fetchall():
                # Get ingredients for each recipe
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

def test_recipe_repository():
    """Test recipe repository operations."""
    print("🧪 Testing Recipe Repository")
    print("=" * 30)
    
    repo = SimpleRecipeRepository("test_recipes.db")
    
    # Create test user
    user_id = str(uuid.uuid4())
    with sqlite3.connect("test_recipes.db") as conn:
        conn.execute("INSERT INTO users (id, name) VALUES (?, ?)", (user_id, "Test User"))
    
    # Test 1: Create recipe
    print("1. Creating recipe...")
    recipe = Recipe(
        name="Chicken Stir Fry",
        ingredients=[
            Ingredient("Chicken Breast", Decimal("16"), "oz"),
            Ingredient("Bell Pepper", Decimal("6"), "oz"),
            Ingredient("Onion", Decimal("8"), "oz")
        ],
        base_servings=4,
        calories_per_serving=350
    )
    
    recipe_id = repo.save_recipe(recipe, user_id)
    print(f"   ✅ Created recipe: {recipe.name} (ID: {recipe_id[:8]}...)")
    
    # Test 2: Find recipe
    print("2. Finding recipe...")
    found_recipe = repo.find_recipe(recipe_id, user_id)
    if found_recipe and found_recipe.name == "Chicken Stir Fry":
        print(f"   ✅ Found recipe: {found_recipe.name} with {len(found_recipe.ingredients)} ingredients")
    else:
        print("   ❌ Recipe not found")
        return
    
    # Test 3: Verify ingredients
    print("3. Verifying ingredients...")
    ingredient_names = [ing.name for ing in found_recipe.ingredients]
    if "Chicken Breast" in ingredient_names and "Bell Pepper" in ingredient_names:
        print(f"   ✅ Ingredients correct: {', '.join(ingredient_names)}")
    else:
        print("   ❌ Ingredients incorrect")
        return
    
    # Test 4: Get user recipes
    print("4. Getting user recipes...")
    user_recipes = repo.get_user_recipes(user_id)
    if len(user_recipes) == 1 and user_recipes[0].name == "Chicken Stir Fry":
        print(f"   ✅ Found {len(user_recipes)} recipe(s) for user")
    else:
        print("   ❌ User recipes incorrect")
        return
    
    print("\n🎉 All tests passed! Recipe Repository working correctly.")
    
    # Cleanup
    import os
    os.remove("test_recipes.db")
    print("🧹 Test database cleaned up.")

if __name__ == "__main__":
    test_recipe_repository()
