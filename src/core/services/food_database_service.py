"""
Food Database Service — searches real public nutrition databases.

This service is the single entry point the rest of the app uses to find
foods by name. It tries, in order:

1. The local offline sample database (instant, ships with the app).
2. USDA FoodData Central — government-curated, per-100g for SR Legacy /
   Foundation foods, per-package for Branded foods.
3. Open Food Facts — community database of branded packaged products.

Each result is returned as a `FoodItem` whose `unit` is the *serving label*
the source database reported the calories under (e.g. "100g", "1 cup",
"1 large egg"). The picker UI shows that label so the user always knows
what one "serving" means before adding it to a recipe or food log.

Network calls are sync and short-timeout (5s). On failure we log to stderr
and keep going with whatever results we already have — the app stays
usable when offline.
"""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional

import requests

# Import from core layer
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.domain.models import FoodItem


# USDA FoodData Central nutrient IDs.
_USDA_NUTRIENT_CALORIES = 1008  # Energy (kcal)
_USDA_NUTRIENT_PROTEIN = 1003
_USDA_NUTRIENT_CARBS = 1005
_USDA_NUTRIENT_FAT = 1004

_HTTP_TIMEOUT_SECONDS = 5


class FoodDatabaseService:
    """Search service over USDA + Open Food Facts + offline sample data."""

    def __init__(self, *, network_enabled: bool = True):
        """
        Args:
            network_enabled: When False, skip live API calls and only return
                sample-DB matches. Set False in tests to keep them offline
                and fast.
        """
        self.network_enabled = network_enabled
        self.databases = {
            "usda": {
                "name": "USDA FoodData Central",
                "base_url": "https://api.nal.usda.gov/fdc/v1",
                "api_key": "8HGmowNL9HfUaT7k6vfZs7EKNnZleBno7Xo0dMj4",
                "enabled": True,
            },
            "openfoodfacts": {
                "name": "Open Food Facts",
                "base_url": "https://world.openfoodfacts.org/cgi/search.pl",
                "api_key": None,
                "enabled": True,
            },
        }
        self._sample_database = self._create_comprehensive_sample_database()

    # ---------------------------------------------------------------- public API

    def search_food_database(self, query: str, category: Optional[str] = None,
                             limit: int = 20) -> List[FoodItem]:
        """Search across all available sources. Sample DB first (instant),
        then USDA, then Open Food Facts. Deduped on (source, food_id) or name.
        """
        results: List[FoodItem] = []
        seen_keys: set = set()

        def _add(items: List[FoodItem]) -> None:
            for it in items:
                key = (it.source, it.food_id) if it.food_id else ("name", it.name.lower())
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                results.append(it)
                if len(results) >= limit:
                    return

        _add(self._search_sample_database(query, category))
        if len(results) >= limit or not self.network_enabled:
            return results

        _add(self._search_usda(query, limit=limit))
        if len(results) >= limit:
            return results

        _add(self._search_openfoodfacts(query, limit=limit))
        return results

    def get_database_info(self) -> Dict[str, Dict]:
        """Information about which sources are configured. Useful for the
        admin/diagnostic UI down the road."""
        return {
            name: {
                "name": cfg["name"],
                "enabled": cfg["enabled"],
                "requires_api_key": cfg["api_key"] is not None,
            }
            for name, cfg in self.databases.items()
        }

    # --------------------------------------------------------------- USDA

    def _search_usda(self, query: str, limit: int) -> List[FoodItem]:
        cfg = self.databases["usda"]
        if not cfg["enabled"]:
            return []
        try:
            response = requests.get(
                f"{cfg['base_url']}/foods/search",
                params={
                    "query": query,
                    "pageSize": limit,
                    "api_key": cfg["api_key"],
                },
                timeout=_HTTP_TIMEOUT_SECONDS,
            )
            if response.status_code != 200:
                print(f"USDA API returned {response.status_code}", file=sys.stderr)
                return []
            return _parse_usda_response(response.json())
        except (requests.RequestException, ValueError) as e:
            print(f"USDA API error: {e}", file=sys.stderr)
            return []

    # --------------------------------------------------------------- Open Food Facts

    def _search_openfoodfacts(self, query: str, limit: int) -> List[FoodItem]:
        cfg = self.databases["openfoodfacts"]
        if not cfg["enabled"]:
            return []
        try:
            response = requests.get(
                cfg["base_url"],
                params={
                    "search_terms": query,
                    "search_simple": 1,
                    "action": "process",
                    "json": 1,
                    "page_size": limit,
                },
                headers={"User-Agent": "meal-planner-v1/0.1 (educational)"},
                timeout=_HTTP_TIMEOUT_SECONDS,
            )
            if response.status_code != 200:
                print(f"Open Food Facts returned {response.status_code}", file=sys.stderr)
                return []
            return _parse_openfoodfacts_response(response.json())
        except (requests.RequestException, ValueError) as e:
            print(f"Open Food Facts error: {e}", file=sys.stderr)
            return []

    # --------------------------------------------------------------- sample data

    def _search_sample_database(self, query: str,
                                category: Optional[str] = None) -> List[FoodItem]:
        q = query.lower()
        return [
            item for item in self._sample_database
            if q in item.name.lower()
            and (category is None or item.category == category)
        ]

    def _create_comprehensive_sample_database(self) -> List[FoodItem]:
        """Sample nutrition database used as the offline fallback for food
        searches. All "100g" entries report calories per 100 grams; "piece"
        entries report calories per typical-size unit."""
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

            # Grains / starches.
            FoodItem("White Rice Cooked", 130, Decimal('2.7'), Decimal('28'), Decimal('0.3'), "100g", "grain", "sample"),
            FoodItem("White Rice Dry", 365, Decimal('7'), Decimal('80'), Decimal('0.7'), "100g", "grain", "sample"),
            FoodItem("Basmati Rice Dry", 360, Decimal('7.5'), Decimal('78'), Decimal('0.9'), "100g", "grain", "sample"),
            FoodItem("Brown Rice Cooked", 123, Decimal('2.6'), Decimal('23'), Decimal('0.9'), "100g", "grain", "sample"),
            FoodItem("Oats Rolled Dry", 389, Decimal('17'), Decimal('66'), Decimal('7'), "100g", "grain", "sample"),
            FoodItem("Spaghetti Dry", 371, Decimal('13'), Decimal('75'), Decimal('1.5'), "100g", "grain", "sample"),
            FoodItem("Chow Mein Noodles", 286, Decimal('5'), Decimal('38'), Decimal('14'), "100g", "grain", "sample"),
            FoodItem("Brioche Bun", 220, Decimal('7'), Decimal('29'), Decimal('8'), "piece", "grain", "sample"),
            FoodItem("Idaho Potato", 161, Decimal('4.3'), Decimal('37'), Decimal('0.2'), "piece", "vegetable", "sample"),

            # Vegetables / herbs.
            FoodItem("Broccoli", 34, Decimal('2.8'), Decimal('7'), Decimal('0.4'), "100g", "vegetable", "sample"),
            FoodItem("Spinach", 23, Decimal('2.9'), Decimal('3.6'), Decimal('0.4'), "100g", "vegetable", "sample"),
            FoodItem("Zucchini", 17, Decimal('1.2'), Decimal('3.1'), Decimal('0.3'), "100g", "vegetable", "sample"),
            FoodItem("Bell Pepper", 31, Decimal('1'), Decimal('7'), Decimal('0.3'), "piece", "vegetable", "sample"),
            FoodItem("Onion", 44, Decimal('1.2'), Decimal('10'), Decimal('0.1'), "piece", "vegetable", "sample"),
            FoodItem("Garlic Clove", 4, Decimal('0.2'), Decimal('1'), zero, "piece", "herb", "sample"),

            # Fats / oils.
            FoodItem("Olive Oil", 884, zero, zero, Decimal('100'), "100g", "oil", "sample"),
            FoodItem("Butter", 717, Decimal('0.9'), Decimal('0.1'), Decimal('81'), "100g", "fat", "sample"),

            # Sauces / condiments.
            FoodItem("Soy Sauce", 53, Decimal('8'), Decimal('5'), Decimal('0.6'), "100g", "sauce", "sample"),
            FoodItem("Hoisin Sauce", 220, Decimal('3.3'), Decimal('44'), Decimal('3.4'), "100g", "sauce", "sample"),
            FoodItem("Honey", 304, Decimal('0.3'), Decimal('82'), zero, "100g", "sauce", "sample"),

            # Dairy.
            FoodItem("Greek Yogurt Nonfat", 59, Decimal('10'), Decimal('3.6'), Decimal('0.4'), "100g", "dairy", "sample"),
            FoodItem("Milk 2 Percent", 50, Decimal('3.3'), Decimal('4.8'), Decimal('2'), "100g", "dairy", "sample"),
            FoodItem("Cheddar Cheese", 403, Decimal('25'), Decimal('1.3'), Decimal('33'), "100g", "dairy", "sample"),

            # Spices (negligible at typical doses, included for completeness).
            FoodItem("Salt", 0, zero, zero, zero, "100g", "spice", "sample"),
            FoodItem("Black Pepper", 251, Decimal('10'), Decimal('64'), Decimal('3.3'), "100g", "spice", "sample"),
            FoodItem("Garlic Powder", 331, Decimal('17'), Decimal('73'), Decimal('0.7'), "100g", "spice", "sample"),
        ]


# ----------------------------------------------------------- USDA response parsing

def _parse_usda_response(data: Dict) -> List[FoodItem]:
    """Convert a USDA `/foods/search` payload into FoodItems.

    USDA returns two flavors of food rows:
    - SR Legacy / Foundation foods: nutrients are per 100g. Serving label = "100g".
    - Branded foods: have `servingSize` (number) + `servingSizeUnit` (g/ml) and
      sometimes `householdServingFullText` ("1 cup (240 mL)"). Branded foods'
      foodNutrients are also per 100g, so we scale them to the package serving.
    """
    items: List[FoodItem] = []
    for food in data.get("foods", []):
        try:
            nutrients_per_100 = {
                n["nutrientId"]: n.get("value", 0)
                for n in food.get("foodNutrients", [])
                if "nutrientId" in n
            }
            cal_per_100 = nutrients_per_100.get(_USDA_NUTRIENT_CALORIES, 0) or 0
            pro_per_100 = nutrients_per_100.get(_USDA_NUTRIENT_PROTEIN, 0) or 0
            carb_per_100 = nutrients_per_100.get(_USDA_NUTRIENT_CARBS, 0) or 0
            fat_per_100 = nutrients_per_100.get(_USDA_NUTRIENT_FAT, 0) or 0

            data_type = food.get("dataType", "")
            serving_label, scale = _usda_serving_label_and_scale(food, data_type)

            items.append(FoodItem(
                name=food.get("description", "Unknown"),
                calories_per_unit=int(round(cal_per_100 * scale)),
                protein_per_unit=Decimal(str(pro_per_100 * scale)).quantize(Decimal("0.01")),
                carbs_per_unit=Decimal(str(carb_per_100 * scale)).quantize(Decimal("0.01")),
                fats_per_unit=Decimal(str(fat_per_100 * scale)).quantize(Decimal("0.01")),
                unit=serving_label,
                category="food",
                source="usda",
                food_id=str(food.get("fdcId")),
                brand=food.get("brandOwner") or food.get("brandName"),
            ))
        except Exception as e:  # malformed row — skip rather than crash the whole search
            print(f"Skipping bad USDA row: {e}", file=sys.stderr)
            continue
    return items


def _usda_serving_label_and_scale(food: Dict, data_type: str) -> tuple[str, float]:
    """Return (serving_label, scale) where scale multiplies per-100g values
    to per-serving values."""
    if data_type == "Branded":
        serving_size = food.get("servingSize")
        unit = (food.get("servingSizeUnit") or "g").lower()
        household = food.get("householdServingFullText")
        if serving_size and unit in ("g", "ml"):  # treat ml ~ g for liquids
            label = household or f"{_fmt_num(serving_size)} {unit}"
            return label, float(serving_size) / 100.0
        if household:
            return household, 1.0  # no scale info available, leave per-100g values
    # Foundation / SR Legacy foods don't have a meaningful serving — use 100g.
    return "100g", 1.0


def _fmt_num(n) -> str:
    try:
        f = float(n)
    except (TypeError, ValueError):
        return str(n)
    return f"{int(f)}" if f.is_integer() else f"{f:g}"


# ------------------------------------------------- Open Food Facts response parsing

def _parse_openfoodfacts_response(data: Dict) -> List[FoodItem]:
    """Convert an Open Food Facts search payload into FoodItems.

    OFF reports nutrients per 100g in `nutriments`. If the product carries a
    `serving_size` field ("28 g") and per-serving values, we prefer those.
    """
    items: List[FoodItem] = []
    for product in data.get("products", []):
        try:
            nutriments = product.get("nutriments", {}) or {}
            name = (product.get("product_name") or "").strip()
            if not name:
                continue

            cal_serving = nutriments.get("energy-kcal_serving")
            if cal_serving is not None and product.get("serving_size"):
                serving_label = product["serving_size"]
                cal = int(round(float(cal_serving)))
                pro = Decimal(str(nutriments.get("proteins_serving") or 0))
                carb = Decimal(str(nutriments.get("carbohydrates_serving") or 0))
                fat = Decimal(str(nutriments.get("fat_serving") or 0))
            else:
                serving_label = "100g"
                cal = int(round(float(nutriments.get("energy-kcal_100g") or 0)))
                pro = Decimal(str(nutriments.get("proteins_100g") or 0))
                carb = Decimal(str(nutriments.get("carbohydrates_100g") or 0))
                fat = Decimal(str(nutriments.get("fat_100g") or 0))

            items.append(FoodItem(
                name=name,
                calories_per_unit=cal,
                protein_per_unit=pro,
                carbs_per_unit=carb,
                fats_per_unit=fat,
                unit=serving_label,
                category="food",
                source="openfoodfacts",
                food_id=product.get("code"),
                brand=(product.get("brands") or "").split(",")[0].strip() or None,
            ))
        except Exception as e:
            print(f"Skipping bad OFF row: {e}", file=sys.stderr)
            continue
    return items
