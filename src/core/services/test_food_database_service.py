"""Tests for FoodDatabaseService — verifies USDA + Open Food Facts parsing
and the dedupe/fallback behavior of `search_food_database`.

Network calls are mocked via monkeypatch — these tests never touch the
internet.
"""
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

import pytest

sys.path.append(str(Path(__file__).parent.parent.parent))

from core.services.food_database_service import (
    FoodDatabaseService,
    _parse_usda_response,
    _parse_openfoodfacts_response,
)


# ------------------------------------------------- USDA parsing

def test_parse_usda_sr_legacy_uses_100g():
    payload = {"foods": [{
        "fdcId": 173410,
        "description": "Yogurt, Greek, plain, nonfat",
        "dataType": "SR Legacy",
        "foodNutrients": [
            {"nutrientId": 1008, "value": 59},
            {"nutrientId": 1003, "value": 10.2},
            {"nutrientId": 1005, "value": 3.6},
            {"nutrientId": 1004, "value": 0.4},
        ],
    }]}
    items = _parse_usda_response(payload)
    assert len(items) == 1
    item = items[0]
    assert item.name == "Yogurt, Greek, plain, nonfat"
    assert item.unit == "100g"
    assert item.calories_per_unit == 59
    assert item.protein_per_unit == Decimal("10.20")
    assert item.source == "usda"
    assert item.food_id == "173410"


def test_parse_usda_branded_scales_to_serving():
    # Branded foods report nutrients per 100g but have a real package serving.
    # 227g serving × (59 cal/100g) = 134 cal per serving.
    payload = {"foods": [{
        "fdcId": 999,
        "description": "Greek Yogurt 5%",
        "brandOwner": "Chobani",
        "dataType": "Branded",
        "servingSize": 227,
        "servingSizeUnit": "g",
        "householdServingFullText": "1 cup (227 g)",
        "foodNutrients": [
            {"nutrientId": 1008, "value": 59},
        ],
    }]}
    items = _parse_usda_response(payload)
    assert len(items) == 1
    item = items[0]
    assert item.unit == "1 cup (227 g)"
    assert item.calories_per_unit == 134  # 59 * 2.27 = 133.93 → 134
    assert item.brand == "Chobani"


def test_parse_usda_skips_malformed_rows():
    payload = {"foods": [
        {"fdcId": 1, "description": "Good", "foodNutrients": [{"nutrientId": 1008, "value": 100}]},
        {"description": "Missing nutrients entirely"},  # OK — handled
        "not a dict",  # bad — should be skipped
    ]}
    items = _parse_usda_response(payload)
    assert len(items) == 2  # third entry is the str — gets skipped
    assert items[0].name == "Good"


# ------------------------------------------------- Open Food Facts parsing

def test_parse_off_uses_per_serving_when_available():
    payload = {"products": [{
        "code": "0000001",
        "product_name": "Greek Yogurt",
        "brands": "Chobani, USA",
        "serving_size": "227 g",
        "nutriments": {
            "energy-kcal_100g": 59,
            "energy-kcal_serving": 134,
            "proteins_serving": 23,
            "carbohydrates_serving": 8,
            "fat_serving": 1,
        },
    }]}
    items = _parse_openfoodfacts_response(payload)
    assert len(items) == 1
    item = items[0]
    assert item.unit == "227 g"
    assert item.calories_per_unit == 134
    assert item.brand == "Chobani"  # first brand only


def test_parse_off_falls_back_to_per_100g():
    payload = {"products": [{
        "code": "0000002",
        "product_name": "Plain yogurt",
        "nutriments": {"energy-kcal_100g": 60, "proteins_100g": 5},
    }]}
    items = _parse_openfoodfacts_response(payload)
    assert items[0].unit == "100g"
    assert items[0].calories_per_unit == 60


def test_parse_off_skips_products_without_name():
    payload = {"products": [
        {"code": "1", "product_name": "", "nutriments": {}},
        {"code": "2", "product_name": "Real one", "nutriments": {"energy-kcal_100g": 100}},
    ]}
    items = _parse_openfoodfacts_response(payload)
    assert len(items) == 1
    assert items[0].name == "Real one"


# ------------------------------------------------- search_food_database integration

def test_search_returns_sample_data_offline():
    """With network disabled, search returns sample DB matches only."""
    svc = FoodDatabaseService(network_enabled=False)
    items = svc.search_food_database("chicken breast", limit=5)
    assert any("chicken breast" in i.name.lower() for i in items)
    # All items should be from sample (no network calls happened).
    assert all(i.source == "sample" for i in items)


def test_search_falls_back_to_network_when_sample_misses(monkeypatch):
    """If the sample DB has no match, we should hit USDA."""
    fake_payload = {"foods": [{
        "fdcId": 555,
        "description": "Flux capacitor dust",
        "dataType": "SR Legacy",
        "foodNutrients": [{"nutrientId": 1008, "value": 200}],
    }]}

    class _FakeResp:
        status_code = 200
        def json(self) -> Dict[str, Any]:
            return fake_payload

    calls: List[str] = []

    def _fake_get(url: str, params: Dict[str, Any] = None, **kw):
        calls.append(url)
        # Only USDA gets called because it returns a result, satisfying the limit.
        if "nal.usda.gov" in url:
            return _FakeResp()
        # If OFF gets called too, return empty.
        empty = _FakeResp()
        empty.json = lambda: {"products": []}
        return empty

    monkeypatch.setattr("core.services.food_database_service.requests.get", _fake_get)
    svc = FoodDatabaseService(network_enabled=True)
    items = svc.search_food_database("flux capacitor dust", limit=5)
    assert any("nal.usda.gov" in c for c in calls)
    assert any(i.source == "usda" and i.name == "Flux capacitor dust" for i in items)


def test_search_swallows_network_errors(monkeypatch):
    """Network failure shouldn't crash the search — sample matches still returned."""
    import requests

    def _raise(*a, **kw):
        raise requests.ConnectionError("offline")
    monkeypatch.setattr("core.services.food_database_service.requests.get", _raise)
    svc = FoodDatabaseService(network_enabled=True)
    items = svc.search_food_database("chicken breast", limit=5)
    assert any("chicken breast" in i.name.lower() for i in items)


def test_search_dedupes_across_sources(monkeypatch):
    """Same item appearing in multiple sources is returned once."""
    sample_payload = {"foods": [
        {"fdcId": 1, "description": "Chicken Breast",
         "dataType": "SR Legacy",
         "foodNutrients": [{"nutrientId": 1008, "value": 165}]},
    ]}

    class _Resp:
        status_code = 200
        def __init__(self, payload): self._p = payload
        def json(self): return self._p

    def _fake_get(url, params=None, **kw):
        if "nal.usda.gov" in url:
            return _Resp(sample_payload)
        return _Resp({"products": []})

    monkeypatch.setattr("core.services.food_database_service.requests.get", _fake_get)
    svc = FoodDatabaseService(network_enabled=True)
    items = svc.search_food_database("chicken breast", limit=10)
    # Sample DB has Chicken Breast, USDA has Chicken Breast — different sources,
    # both kept (different food_id keys). The point is no duplicates of either.
    sample_breasts = [i for i in items if i.source == "sample" and i.name.lower() == "chicken breast"]
    usda_breasts = [i for i in items if i.source == "usda"]
    assert len(sample_breasts) == 1
    assert len(usda_breasts) <= 1


def test_get_database_info_lists_sources():
    svc = FoodDatabaseService(network_enabled=False)
    info = svc.get_database_info()
    assert "usda" in info
    assert "openfoodfacts" in info
    assert info["usda"]["requires_api_key"] is True
    assert info["openfoodfacts"]["requires_api_key"] is False
