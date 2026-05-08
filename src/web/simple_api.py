#!/usr/bin/env python3
"""
Simple Flask API for Recipe Builder Demo
Uses sample data for quick testing
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.services.food_database_service import FoodDatabaseService

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Initialize services
food_db = FoodDatabaseService()

# Simple in-memory recipe storage for demo
recipes = []
recipe_counter = 1

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
    global recipe_counter
    data = request.get_json()
    
    if not data or 'name' not in data or 'ingredients' not in data:
        return jsonify({'error': 'Recipe name and ingredients required'}), 400
    
    try:
        recipe = {
            'id': recipe_counter,
            'name': data['name'],
            'description': data.get('description', ''),
            'servings': data.get('servings', 1),
            'prep_time': data.get('prep_time', 0),
            'cook_time': data.get('cook_time', 0),
            'ingredients': data['ingredients'],
            'total_calories': sum(ing.get('calories', 0) for ing in data['ingredients'])
        }
        
        recipes.append(recipe)
        recipe_counter += 1
        
        return jsonify({'recipe_id': recipe['id'], 'message': 'Recipe created successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recipes', methods=['GET'])
def get_recipes():
    """Get all recipes."""
    return jsonify({'recipes': recipes})

@app.route('/')
def index():
    """Serve the recipe builder page."""
    return app.send_static_file('recipe_builder.html')

if __name__ == '__main__':
    print("🍽️ Starting Meal Planner API...")
    print("📱 Recipe Builder: http://localhost:5000/")
    print("🔍 Food Search API: http://localhost:5000/api/foods/search?q=chicken")
    app.run(debug=True, host='0.0.0.0', port=5000)
