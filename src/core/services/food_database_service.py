"""
Food Database Service - Integration with multiple free nutrition databases
Clean Architecture - External Data Integration Layer
"""
import requests
import json
import sys
import time
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Optional, Union

# Import from core layer
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.domain.models import FoodItem  # noqa: F401  (re-exported for legacy callers)

class FoodDatabaseService:
    """Service for searching multiple free food databases."""
    
    def __init__(self):
        """Initialize food database service with real API configurations."""
        self.databases = {
            "usda": {
                "name": "USDA FoodData Central",
                "base_url": "https://api.nal.usda.gov/fdc/v1",
                "api_key": "8HGmowNL9HfUaT7k6vfZs7EKNnZleBno7Xo0dMj4",
                "enabled": True
            },
            "canadian_nutrient_file": {
                "name": "Canadian Nutrient File (CNF)",
                "base_url": "https://food-nutrition.canada.ca/api/canadian-nutrient-file",
                "api_key": None,  # No API key required
                "enabled": True
            },
            "foodb": {
                "name": "FooDB - Food Database",
                "base_url": "https://foodb.ca/api/v1",
                "api_key": None,
                "enabled": True
            },
            "openfoodfacts": {
                "name": "Open Food Facts",
                "base_url": "https://world.openfoodfacts.org/api/v0",
                "api_key": None,  # No API key needed
                "enabled": True
            }
        }
        
        # Enhanced sample database as fallback
        self._sample_database = self._create_comprehensive_sample_database()
    
    def _create_comprehensive_sample_database(self) -> List[FoodItem]:
        """Sample nutrition database used as the offline fallback for food
        searches. All "100g" entries report calories per 100 grams; "piece"
        entries report calories per typical-size unit. The RecipeNutritionEstimator
        uses this set today; live USDA / Open Food Facts integration is the
        upgrade path for accuracy on rarer ingredients.
        """
        zero = Decimal('0')
        return [
            # Proteins (per 100g cooked unless noted).
            FoodItem("Chicken Breast", 165, Decimal('31'), zero, Decimal('3.6'), "100g", "protein", "sample"),
            FoodItem("Chicken Thigh", 209, Decimal('26'), zero, Decimal('11'), "100g", "protein", "sample"),
            FoodItem("Rotisserie Chicken", 190, Decimal('29'), zero, Decimal('8'), "100g", "protein", "sample"),
            FoodItem("Salmon Fillet", 208, Decimal('22'), zero, Decimal('12'), "100g", "protein", "sample"),
            FoodItem("Ground Beef 90 10", 176, Decimal('20'), zero, Decimal('10'), "100g", "protein", "sample"),
            FoodItem("Ground Beef 85 15", 250, Decimal('26'), zero, Decimal('17'), "100g", "protein", "sample"),
            FoodItem("Ground Sausage", 301, Decimal('14'), Decimal('1'), Decimal('27'), "100g", "protein", "sample"),
            FoodItem("NY Strip Steak", 270, Decimal('26'), zero, Decimal('18'), "100g", "protein", "sample"),
            FoodItem("Egg Large", 78, Decimal('6'), Decimal('0.6'), Decimal('5'), "piece", "protein", "sample"),
            FoodItem("Egg White", 17, Decimal('3.6'), Decimal('0.2'), zero, "piece", "protein", "sample"),

            # Grains / starches (per 100g cooked unless noted).
            FoodItem("White Rice Cooked", 130, Decimal('2.7'), Decimal('28'), Decimal('0.3'), "100g", "grain", "sample"),
            FoodItem("White Rice Dry", 365, Decimal('7'), Decimal('80'), Decimal('0.7'), "100g", "grain", "sample"),
            FoodItem("Basmati Rice Dry", 360, Decimal('7.5'), Decimal('78'), Decimal('0.9'), "100g", "grain", "sample"),
            FoodItem("Short Grain Rice Dry", 358, Decimal('6.5'), Decimal('80'), Decimal('0.6'), "100g", "grain", "sample"),
            FoodItem("Brown Rice Cooked", 123, Decimal('2.6'), Decimal('23'), Decimal('0.9'), "100g", "grain", "sample"),
            FoodItem("Oats Rolled Dry", 389, Decimal('17'), Decimal('66'), Decimal('7'), "100g", "grain", "sample"),
            FoodItem("Spaghetti Dry", 371, Decimal('13'), Decimal('75'), Decimal('1.5'), "100g", "grain", "sample"),
            FoodItem("Chow Mein Noodles", 286, Decimal('5'), Decimal('38'), Decimal('14'), "100g", "grain", "sample"),
            FoodItem("Brioche Bun", 220, Decimal('7'), Decimal('29'), Decimal('8'), "piece", "grain", "sample"),
            FoodItem("Corn Flakes", 357, Decimal('7'), Decimal('84'), Decimal('0.4'), "100g", "grain", "sample"),
            FoodItem("Flour", 364, Decimal('10'), Decimal('76'), Decimal('1'), "100g", "grain", "sample"),
            FoodItem("Idaho Potato", 161, Decimal('4.3'), Decimal('37'), Decimal('0.2'), "piece", "vegetable", "sample"),
            FoodItem("Sweet Potato Baked", 103, Decimal('2.3'), Decimal('24'), Decimal('0.1'), "100g", "vegetable", "sample"),

            # Vegetables / herbs.
            FoodItem("Broccoli", 34, Decimal('2.8'), Decimal('7'), Decimal('0.4'), "100g", "vegetable", "sample"),
            FoodItem("Spinach", 23, Decimal('2.9'), Decimal('3.6'), Decimal('0.4'), "100g", "vegetable", "sample"),
            FoodItem("Kale", 49, Decimal('4.3'), Decimal('9'), Decimal('0.9'), "100g", "vegetable", "sample"),
            FoodItem("Bok Choy", 13, Decimal('1.5'), Decimal('2.2'), Decimal('0.2'), "100g", "vegetable", "sample"),
            FoodItem("Gai Lan", 22, Decimal('1.9'), Decimal('3'), Decimal('0.6'), "100g", "vegetable", "sample"),
            FoodItem("Asparagus", 20, Decimal('2.2'), Decimal('3.9'), Decimal('0.1'), "100g", "vegetable", "sample"),
            FoodItem("Zucchini", 17, Decimal('1.2'), Decimal('3.1'), Decimal('0.3'), "100g", "vegetable", "sample"),
            FoodItem("Cauliflower Rice", 25, Decimal('2'), Decimal('5'), Decimal('0.3'), "100g", "vegetable", "sample"),
            FoodItem("Bell Pepper", 31, Decimal('1'), Decimal('7'), Decimal('0.3'), "piece", "vegetable", "sample"),
            FoodItem("Onion", 44, Decimal('1.2'), Decimal('10'), Decimal('0.1'), "piece", "vegetable", "sample"),
            FoodItem("Yellow Onion", 44, Decimal('1.2'), Decimal('10'), Decimal('0.1'), "piece", "vegetable", "sample"),
            FoodItem("Carrot", 25, Decimal('0.6'), Decimal('6'), Decimal('0.1'), "piece", "vegetable", "sample"),
            FoodItem("Shredded Carrots", 41, Decimal('0.9'), Decimal('10'), Decimal('0.2'), "100g", "vegetable", "sample"),
            FoodItem("Celery", 6, Decimal('0.3'), Decimal('1.2'), zero, "piece", "vegetable", "sample"),
            FoodItem("Roma Tomato", 22, Decimal('1.1'), Decimal('4.8'), Decimal('0.2'), "piece", "vegetable", "sample"),
            FoodItem("Crushed Tomatoes", 32, Decimal('1.5'), Decimal('7'), Decimal('0.3'), "100g", "vegetable", "sample"),
            FoodItem("Tomato Paste", 82, Decimal('4.3'), Decimal('19'), Decimal('0.5'), "100g", "vegetable", "sample"),
            FoodItem("Black Beans Canned", 91, Decimal('6'), Decimal('16'), Decimal('0.3'), "100g", "legume", "sample"),
            FoodItem("Napa Cabbage", 13, Decimal('1.2'), Decimal('2.4'), Decimal('0.2'), "100g", "vegetable", "sample"),
            FoodItem("Bean Sprouts", 30, Decimal('3'), Decimal('6'), Decimal('0.2'), "100g", "vegetable", "sample"),
            FoodItem("Green Onion", 5, Decimal('0.3'), Decimal('1.1'), zero, "piece", "vegetable", "sample"),
            FoodItem("Spring Onion", 5, Decimal('0.3'), Decimal('1.1'), zero, "piece", "vegetable", "sample"),
            FoodItem("Cucumber", 45, Decimal('2'), Decimal('11'), Decimal('0.3'), "piece", "vegetable", "sample"),
            FoodItem("Cilantro", 23, Decimal('2.1'), Decimal('3.7'), Decimal('0.5'), "100g", "herb", "sample"),
            FoodItem("Parsley", 36, Decimal('3'), Decimal('6'), Decimal('0.8'), "100g", "herb", "sample"),
            FoodItem("Garlic Clove", 4, Decimal('0.2'), Decimal('1'), zero, "piece", "herb", "sample"),
            FoodItem("Ginger", 80, Decimal('1.8'), Decimal('18'), Decimal('0.8'), "100g", "herb", "sample"),
            FoodItem("Rosemary Sprig", 2, zero, Decimal('0.4'), zero, "piece", "herb", "sample"),

            # Fruits.
            FoodItem("Apple Medium", 95, Decimal('0.5'), Decimal('25'), Decimal('0.3'), "piece", "fruit", "sample"),
            FoodItem("Banana Medium", 105, Decimal('1.3'), Decimal('27'), Decimal('0.4'), "piece", "fruit", "sample"),
            FoodItem("Blueberries", 57, Decimal('0.7'), Decimal('14'), Decimal('0.3'), "100g", "fruit", "sample"),
            FoodItem("Strawberries", 32, Decimal('0.7'), Decimal('7.7'), Decimal('0.3'), "100g", "fruit", "sample"),
            FoodItem("Avocado", 240, Decimal('3'), Decimal('13'), Decimal('22'), "piece", "fruit", "sample"),
            FoodItem("Lemon", 17, Decimal('0.6'), Decimal('5.4'), Decimal('0.2'), "piece", "fruit", "sample"),
            FoodItem("Lime", 20, Decimal('0.5'), Decimal('7'), Decimal('0.1'), "piece", "fruit", "sample"),
            FoodItem("Pineapple", 50, Decimal('0.5'), Decimal('13'), Decimal('0.1'), "100g", "fruit", "sample"),

            # Dairy / cheese.
            FoodItem("Greek Yogurt Nonfat", 59, Decimal('10'), Decimal('3.6'), Decimal('0.4'), "100g", "dairy", "sample"),
            FoodItem("Milk 2 Percent", 50, Decimal('3.3'), Decimal('4.8'), Decimal('2'), "100g", "dairy", "sample"),
            FoodItem("Cheddar Cheese", 403, Decimal('25'), Decimal('1.3'), Decimal('33'), "100g", "dairy", "sample"),
            FoodItem("Mozzarella Reduced Fat", 254, Decimal('24'), Decimal('3.1'), Decimal('16'), "100g", "dairy", "sample"),
            FoodItem("Butter", 717, Decimal('0.9'), Decimal('0.1'), Decimal('81'), "100g", "fat", "sample"),

            # Oils / fats.
            FoodItem("Olive Oil", 884, zero, zero, Decimal('100'), "100g", "oil", "sample"),
            FoodItem("EVOO", 884, zero, zero, Decimal('100'), "100g", "oil", "sample"),
            FoodItem("Avocado Oil", 884, zero, zero, Decimal('100'), "100g", "oil", "sample"),
            FoodItem("Vegetable Oil", 884, zero, zero, Decimal('100'), "100g", "oil", "sample"),
            FoodItem("Grape Seed Oil", 884, zero, zero, Decimal('100'), "100g", "oil", "sample"),
            FoodItem("Sesame Oil", 884, zero, zero, Decimal('100'), "100g", "oil", "sample"),

            # Sauces / condiments.
            FoodItem("Soy Sauce", 53, Decimal('8'), Decimal('5'), Decimal('0.6'), "100g", "sauce", "sample"),
            FoodItem("Hoisin Sauce", 220, Decimal('3.3'), Decimal('44'), Decimal('3.4'), "100g", "sauce", "sample"),
            FoodItem("Rice Vinegar", 18, Decimal('0.3'), Decimal('0.04'), zero, "100g", "sauce", "sample"),
            FoodItem("Sherry Vinegar", 19, Decimal('0.4'), Decimal('0.3'), zero, "100g", "sauce", "sample"),
            FoodItem("Gochujang", 240, Decimal('5'), Decimal('51'), Decimal('1'), "100g", "sauce", "sample"),
            FoodItem("Sriracha", 93, Decimal('1.9'), Decimal('19'), Decimal('0.9'), "100g", "sauce", "sample"),
            FoodItem("Honey", 304, Decimal('0.3'), Decimal('82'), zero, "100g", "sauce", "sample"),
            FoodItem("Hot Honey", 304, Decimal('0.3'), Decimal('82'), zero, "100g", "sauce", "sample"),
            FoodItem("Adobo Sauce", 70, Decimal('1.5'), Decimal('11'), Decimal('2.5'), "100g", "sauce", "sample"),
            FoodItem("Chipotle In Adobo", 95, Decimal('2'), Decimal('15'), Decimal('3'), "100g", "sauce", "sample"),
            FoodItem("Pickle Juice", 11, Decimal('0.4'), Decimal('1.6'), zero, "100g", "sauce", "sample"),
            FoodItem("Cornstarch", 381, Decimal('0.3'), Decimal('91'), zero, "100g", "grain", "sample"),
            FoodItem("Beef Bouillon", 200, Decimal('11'), Decimal('11'), Decimal('13'), "100g", "sauce", "sample"),

            # Spices (calorie contribution is negligible at typical recipe doses).
            FoodItem("Salt", 0, zero, zero, zero, "100g", "spice", "sample"),
            FoodItem("Black Pepper", 251, Decimal('10'), Decimal('64'), Decimal('3.3'), "100g", "spice", "sample"),
            FoodItem("White Pepper", 296, Decimal('10'), Decimal('69'), Decimal('2'), "100g", "spice", "sample"),
            FoodItem("Garlic Powder", 331, Decimal('17'), Decimal('73'), Decimal('0.7'), "100g", "spice", "sample"),
            FoodItem("Onion Powder", 341, Decimal('10'), Decimal('79'), Decimal('1'), "100g", "spice", "sample"),
            FoodItem("Paprika", 282, Decimal('14'), Decimal('54'), Decimal('13'), "100g", "spice", "sample"),
            FoodItem("Smoked Paprika", 282, Decimal('14'), Decimal('54'), Decimal('13'), "100g", "spice", "sample"),
            FoodItem("Cumin", 375, Decimal('18'), Decimal('44'), Decimal('22'), "100g", "spice", "sample"),
            FoodItem("Chili Powder", 282, Decimal('14'), Decimal('50'), Decimal('14'), "100g", "spice", "sample"),
            FoodItem("Chipotle Powder", 324, Decimal('14'), Decimal('56'), Decimal('14'), "100g", "spice", "sample"),
            FoodItem("Ancho Chili Powder", 308, Decimal('11'), Decimal('51'), Decimal('15'), "100g", "spice", "sample"),
            FoodItem("Oregano", 265, Decimal('9'), Decimal('69'), Decimal('4.3'), "100g", "spice", "sample"),
            FoodItem("Five Spice Powder", 360, Decimal('5'), Decimal('70'), Decimal('11'), "100g", "spice", "sample"),
            FoodItem("Gochugaru", 282, Decimal('14'), Decimal('54'), Decimal('13'), "100g", "spice", "sample"),
            FoodItem("Togarashi", 282, Decimal('14'), Decimal('54'), Decimal('13'), "100g", "spice", "sample"),
            FoodItem("Chili Flakes", 282, Decimal('14'), Decimal('54'), Decimal('13'), "100g", "spice", "sample"),
            FoodItem("Sesame Seeds", 573, Decimal('18'), Decimal('23'), Decimal('50'), "100g", "spice", "sample"),
            FoodItem("Porcini Powder", 296, Decimal('11'), Decimal('59'), Decimal('1'), "100g", "spice", "sample"),
            FoodItem("Sweetener Splenda", 0, zero, zero, zero, "piece", "spice", "sample"),
        ]
    
    async def search_usda_database(self, query: str, limit: int = 10) -> List[FoodItem]:
        """
        Search USDA FoodData Central database.
        
        Args:
            query: Search term
            limit: Maximum results to return
            
        Returns:
            List of food items from USDA database
        """
        if not self.databases["usda"]["enabled"]:
            return []
        
        try:
            # USDA FoodData Central API
            url = f"{self.databases['usda']['base_url']}/foods/search"
            params = {
                "query": query,
                "pageSize": limit,
                "dataType": ["Foundation", "SR Legacy"],  # High quality data types
                "sortBy": "dataType.keyword",
                "sortOrder": "asc"
            }
            
            # Add API key if available
            if self.databases["usda"]["api_key"]:
                params["api_key"] = self.databases["usda"]["api_key"]
            
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_usda_response(data)
            
        except Exception as e:
            print(f"USDA API error: {e}")
        
        return []
    
    async def search_cnf(self, query: str, limit: int = 10) -> List[FoodItem]:
        """
        Search Canadian Nutrient File database.
        
        Args:
            query: Search term
            limit: Maximum results to return
            
        Returns:
            List of food items from CNF database
        """
        if not self.databases["canadian_nutrient_file"]["enabled"]:
            return []
        
        try:
            url = f"{self.databases['canadian_nutrient_file']['base_url']}/food"
            params = {
                "lang": "en",
                "type": "json",
                "id": query  # CNF uses food codes, would need search endpoint
            }
            
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_cnf_response(data)
                
        except Exception as e:
            print(f"CNF API error: {e}")
            
        return []

    async def search_foodb(self, query: str, limit: int = 10) -> List[FoodItem]:
        """
        Search FooDB database.
        
        Args:
            query: Search term
            limit: Maximum results to return
            
        Returns:
            List of food items from FooDB
        """
        if not self.databases["foodb"]["enabled"]:
            return []
        
        try:
            url = f"{self.databases['foodb']['base_url']}/foods"
            params = {
                "q": query,
                "limit": limit
            }
            
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_foodb_response(data)
                
        except Exception as e:
            print(f"FooDB API error: {e}")
            
        return []
        """
        Search Open Food Facts database.
        
        Args:
            query: Search term
            limit: Maximum results to return
            
        Returns:
            List of food items from Open Food Facts
        """
        if not self.databases["openfoodfacts"]["enabled"]:
            return []
        
        try:
            url = f"{self.databases['openfoodfacts']['base_url']}/product"
            params = {
                "search_terms": query,
                "search_simple": 1,
                "action": "process",
                "json": 1,
                "page_size": limit
            }
            
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_openfoodfacts_response(data)
                
        except Exception as e:
            print(f"Open Food Facts API error: {e}")
        
        return []
    
    def search_food_database(self, query: str, category: Optional[str] = None, 
                           limit: int = 20) -> List[FoodItem]:
        """
        Search across all available food databases.
        
        Args:
            query: Search term
            category: Optional category filter
            limit: Maximum total results
            
        Returns:
            Combined results from all databases
        """
        results = []
        
        # Search sample database first (always available)
        sample_results = self._search_sample_database(query, category)
        results.extend(sample_results[:limit//2])  # Reserve half for API results
        
        # Search external APIs (would be async in production)
        try:
            # Note: In production, these would be async calls
            # For now, using sample database as primary source
            
            # Placeholder for USDA API integration
            # usda_results = await self.search_usda_database(query, limit//4)
            # results.extend(usda_results)
            
            # Placeholder for Open Food Facts integration  
            # off_results = await self.search_openfoodfacts(query, limit//4)
            # results.extend(off_results)
            
            pass
            
        except Exception as e:
            print(f"External API search error: {e}")
        
        # Remove duplicates and limit results
        seen_names = set()
        unique_results = []
        
        for item in results:
            if item.name.lower() not in seen_names:
                seen_names.add(item.name.lower())
                unique_results.append(item)
                
                if len(unique_results) >= limit:
                    break
        
        return unique_results
    
    def _search_sample_database(self, query: str, category: Optional[str] = None) -> List[FoodItem]:
        """Search the comprehensive sample database."""
        results = []
        query_lower = query.lower()
        
        for food_item in self._sample_database:
            # Check if query matches name
            if query_lower in food_item.name.lower():
                # Check category filter if provided
                if category is None or food_item.category == category:
                    results.append(food_item)
        
        return results
    
    def _parse_usda_response(self, data: Dict) -> List[FoodItem]:
        """Parse USDA API response into FoodItem objects."""
        items = []
        
        for food in data.get("foods", []):
            try:
                # Extract nutrition data from USDA format
                nutrients = {n["nutrientId"]: n["value"] for n in food.get("foodNutrients", [])}
                
                # USDA nutrient IDs
                calories = nutrients.get(1008, 0)  # Energy
                protein = nutrients.get(1003, 0)   # Protein
                carbs = nutrients.get(1005, 0)     # Carbohydrates
                fats = nutrients.get(1004, 0)      # Total lipid (fat)
                
                item = FoodItem(
                    name=food.get("description", "Unknown"),
                    calories_per_unit=int(calories),
                    protein_per_unit=Decimal(str(protein)),
                    carbs_per_unit=Decimal(str(carbs)),
                    fats_per_unit=Decimal(str(fats)),
                    unit="100g",  # USDA data is per 100g
                    category="food",
                    source="usda",
                    food_id=str(food.get("fdcId"))
                )
                
                items.append(item)
                
            except Exception as e:
                continue  # Skip malformed entries
        
        return items
    
    def _parse_cnf_response(self, data: Dict) -> List[FoodItem]:
        """Parse Canadian Nutrient File API response."""
        foods = []
        
        try:
            if "foods" in data:
                for item in data["foods"][:10]:
                    name = item.get("food_description", "Unknown Food")
                    
                    # Extract nutrients (CNF provides detailed nutrient data)
                    nutrients = item.get("nutrients", {})
                    calories = nutrients.get("energy_kcal", 0)
                    protein = Decimal(str(nutrients.get("protein", 0)))
                    carbs = Decimal(str(nutrients.get("carbohydrate", 0)))
                    fat = Decimal(str(nutrients.get("fat", 0)))
                    
                    foods.append(FoodItem(
                        name=name,
                        calories_per_unit=int(calories),
                        protein_per_unit=protein,
                        carbs_per_unit=carbs,
                        fats_per_unit=fat,
                        unit="100g",
                        category="food",
                        source="canadian_nutrient_file"
                    ))
        except Exception as e:
            print(f"Error parsing CNF response: {e}")
            
        return foods

    def _parse_foodb_response(self, data: Dict) -> List[FoodItem]:
        """Parse FooDB API response."""
        foods = []
        
        try:
            if "foods" in data:
                for item in data["foods"][:10]:
                    name = item.get("name", "Unknown Food")
                    
                    # FooDB focuses on chemical constituents, may need different parsing
                    nutrients = item.get("nutrients", {})
                    calories = nutrients.get("energy", 0)
                    protein = Decimal(str(nutrients.get("protein", 0)))
                    carbs = Decimal(str(nutrients.get("carbohydrates", 0)))
                    fat = Decimal(str(nutrients.get("fat", 0)))
                    
                    foods.append(FoodItem(
                        name=name,
                        calories_per_unit=int(calories),
                        protein_per_unit=protein,
                        carbs_per_unit=carbs,
                        fats_per_unit=fat,
                        unit="100g",
                        category="food",
                        source="foodb"
                    ))
        except Exception as e:
            print(f"Error parsing FooDB response: {e}")
            
        return foods
        """Parse Open Food Facts API response into FoodItem objects."""
        items = []
        
        for product in data.get("products", []):
            try:
                nutriments = product.get("nutriments", {})
                
                calories = nutriments.get("energy-kcal_100g", 0)
                protein = nutriments.get("proteins_100g", 0)
                carbs = nutriments.get("carbohydrates_100g", 0)
                fats = nutriments.get("fat_100g", 0)
                
                item = FoodItem(
                    name=product.get("product_name", "Unknown"),
                    calories_per_unit=int(calories),
                    protein_per_unit=Decimal(str(protein)),
                    carbs_per_unit=Decimal(str(carbs)),
                    fats_per_unit=Decimal(str(fats)),
                    unit="100g",
                    category="food",
                    source="openfoodfacts",
                    food_id=product.get("code"),
                    brand=product.get("brands")
                )
                
                items.append(item)
                
            except Exception as e:
                continue
        
        return items
    
    def get_database_info(self) -> Dict[str, Dict]:
        """Get information about available databases."""
        return {
            name: {
                "name": config["name"],
                "enabled": config["enabled"],
                "requires_api_key": config["api_key"] is not None
            }
            for name, config in self.databases.items()
        }
