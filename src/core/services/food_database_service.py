"""
Food Database Service - Integration with multiple free nutrition databases
Clean Architecture - External Data Integration Layer
"""
import requests
import json
from decimal import Decimal
from typing import List, Dict, Optional, Union
from dataclasses import dataclass
import time

@dataclass
class FoodItem:
    """Enhanced food item with database source tracking.

    Macros and calories are expressed per `unit` (e.g. per piece, per scoop, per 100g).
    """
    name: str
    calories_per_unit: int
    protein_per_unit: Decimal
    carbs_per_unit: Decimal
    fats_per_unit: Decimal
    unit: str
    category: str  # "food" or "restaurant"
    source: str  # Track which database this came from
    food_id: Optional[str] = None  # Original database ID
    brand: Optional[str] = None

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
        """Create comprehensive sample database with NCCDB/CRDB style data."""
        return [
            # Proteins
            FoodItem("Chicken Breast, Raw", 165, Decimal('31'), Decimal('0'), Decimal('3.6'), "100g", "protein", "sample"),
            FoodItem("Salmon Fillet, Raw", 208, Decimal('22'), Decimal('0'), Decimal('12'), "100g", "protein", "sample"),
            FoodItem("Ground Beef, 85% Lean", 250, Decimal('26'), Decimal('0'), Decimal('15'), "100g", "protein", "sample"),
            FoodItem("Eggs, Large", 155, Decimal('13'), Decimal('1.1'), Decimal('11'), "100g", "protein", "sample"),
            
            # Carbohydrates
            FoodItem("Brown Rice, Cooked", 123, Decimal('2.6'), Decimal('23'), Decimal('0.9'), "100g", "grain", "sample"),
            FoodItem("Quinoa, Cooked", 120, Decimal('4.4'), Decimal('22'), Decimal('1.9'), "100g", "grain", "sample"),
            FoodItem("Sweet Potato, Baked", 103, Decimal('2.3'), Decimal('24'), Decimal('0.1'), "100g", "vegetable", "sample"),
            FoodItem("Oats, Rolled, Dry", 389, Decimal('16.9'), Decimal('66'), Decimal('6.9'), "100g", "grain", "sample"),
            
            # Fruits
            FoodItem("Apple, Medium", 95, Decimal('0.5'), Decimal('25'), Decimal('0.3'), "piece", "fruit", "sample"),
            FoodItem("Banana, Medium", 105, Decimal('1.3'), Decimal('27'), Decimal('0.4'), "piece", "fruit", "sample"),
            FoodItem("Blueberries, Fresh", 57, Decimal('0.7'), Decimal('14'), Decimal('0.3'), "100g", "fruit", "sample"),
            FoodItem("Strawberries, Fresh", 32, Decimal('0.7'), Decimal('7.7'), Decimal('0.3'), "100g", "fruit", "sample"),
            
            # Vegetables
            FoodItem("Broccoli, Raw", 34, Decimal('2.8'), Decimal('7'), Decimal('0.4'), "100g", "vegetable", "sample"),
            FoodItem("Spinach, Raw", 23, Decimal('2.9'), Decimal('3.6'), Decimal('0.4'), "100g", "vegetable", "sample"),
            FoodItem("Bell Pepper, Red", 31, Decimal('1'), Decimal('7'), Decimal('0.3'), "100g", "vegetable", "sample"),
            
            # Fats/Nuts
            FoodItem("Almonds, Raw", 579, Decimal('21'), Decimal('22'), Decimal('50'), "100g", "nuts", "sample"),
            FoodItem("Avocado, Medium", 234, Decimal('2.9'), Decimal('12'), Decimal('21'), "piece", "fruit", "sample"),
            FoodItem("Olive Oil, Extra Virgin", 884, Decimal('0'), Decimal('0'), Decimal('100'), "100g", "oil", "sample"),
            
            # Dairy
            FoodItem("Greek Yogurt, Plain, Nonfat", 59, Decimal('10'), Decimal('3.6'), Decimal('0.4'), "100g", "dairy", "sample"),
            FoodItem("Milk, 2% Fat", 50, Decimal('3.3'), Decimal('4.8'), Decimal('2'), "100ml", "dairy", "sample"),
            FoodItem("Cheddar Cheese", 403, Decimal('25'), Decimal('1.3'), Decimal('33'), "100g", "dairy", "sample"),
            
            # Supplements
            FoodItem("Whey Protein Powder", 120, Decimal('25'), Decimal('3'), Decimal('1'), "scoop", "supplement", "sample"),
            FoodItem("Creatine Monohydrate", 0, Decimal('0'), Decimal('0'), Decimal('0'), "5g", "supplement", "sample"),
            FoodItem("Multivitamin", 0, Decimal('0'), Decimal('0'), Decimal('0'), "tablet", "supplement", "sample"),
            
            # Restaurant/Fast Food (common items)
            FoodItem("McDonald's Big Mac", 550, Decimal('25'), Decimal('45'), Decimal('31'), "piece", "restaurant", "sample"),
            FoodItem("Chipotle Burrito Bowl", 650, Decimal('32'), Decimal('65'), Decimal('25'), "bowl", "restaurant", "sample"),
            FoodItem("Subway 6\" Turkey Breast", 280, Decimal('18'), Decimal('46'), Decimal('3.5'), "sandwich", "restaurant", "sample"),
            FoodItem("Starbucks Grande Latte", 190, Decimal('12'), Decimal('18'), Decimal('7'), "16oz", "restaurant", "sample"),
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
