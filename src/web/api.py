#!/usr/bin/env python3
"""
Flask REST API for Meal Planning App
Exposes core services as HTTP endpoints
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.services.food_database_service import FoodDatabaseService
from core.services.meal_planning_service import MealPlanningService
from repositories.sqlite.recipe_repository import SQLiteRecipeRepository
from repositories.sqlite.user_repository import SQLiteUserRepository

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Initialize services
food_db = FoodDatabaseService()
recipe_repo = SQLiteRecipeRepository()
user_repo = SQLiteUserRepository()
meal_planner = MealPlanningService()

@app.route('/api/foods/search', methods=['GET'])
def search_foods():
    """Search food database for ingredients."""
    query = request.args.get('q', '')
    if not query:
        return jsonify({'error': 'Query parameter required'}), 400
    
    try:
        # Run async search in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(food_db.search_usda_database(query))
        loop.close()

        # Convert to JSON-serializable format
        foods = []
        for food in results:
            foods.append({
                'name': food.name,
                'calories_per_unit': food.calories_per_unit,
                'protein_per_unit': float(food.protein_per_unit),
                'carbs_per_unit': float(food.carbs_per_unit),
                'fats_per_unit': float(food.fats_per_unit),
                'unit': food.unit,
                'category': food.category,
                'source': food.source
            })
        
        return jsonify({'foods': foods})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recipes', methods=['POST'])
def create_recipe():
    """Create new recipe from ingredients."""
    data = request.get_json()
    
    if not data or 'name' not in data or 'ingredients' not in data:
        return jsonify({'error': 'Recipe name and ingredients required'}), 400
    
    try:
        recipe_id = recipe_repo.create_recipe(
            name=data['name'],
            description=data.get('description', ''),
            instructions=data.get('instructions', ''),
            servings=data.get('servings', 1),
            prep_time=data.get('prep_time', 0),
            cook_time=data.get('cook_time', 0),
            ingredients=data['ingredients'],
            household_id=1  # Default household for now
        )
        
        return jsonify({'recipe_id': recipe_id, 'message': 'Recipe created successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recipes', methods=['GET'])
def get_recipes():
    """Get all recipes."""
    try:
        recipes = recipe_repo.get_recipes_by_household(1)  # Default household
        
        # Convert to JSON format
        recipe_list = []
        for recipe in recipes:
            recipe_list.append({
                'id': recipe.id,
                'name': recipe.name,
                'description': recipe.description,
                'servings': recipe.servings,
                'prep_time': recipe.prep_time,
                'cook_time': recipe.cook_time,
                'total_calories': recipe.total_calories,
                'ingredients': [
                    {
                        'name': ing.name,
                        'amount': float(ing.amount),
                        'unit': ing.unit,
                        'calories': ing.calories
                    } for ing in recipe.ingredients
                ]
            })
        
        return jsonify({'recipes': recipe_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
