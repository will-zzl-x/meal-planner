"""Tests for SQLiteIngredientCatalogRepository (slice 8a)."""
import sys
from decimal import Decimal
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from core.domain.models import CatalogIngredient
from repositories.sqlite.ingredient_catalog_repository import SQLiteIngredientCatalogRepository


def _repo(tmp_path) -> SQLiteIngredientCatalogRepository:
    return SQLiteIngredientCatalogRepository(str(tmp_path / "test.db"))


def _sample(name="Greek Yogurt", source="usda", external_id="123") -> CatalogIngredient:
    return CatalogIngredient(
        id="",
        name=name,
        serving_label="100g",
        calories_per_serving=59,
        protein_per_serving=Decimal("10.2"),
        carbs_per_serving=Decimal("3.6"),
        fat_per_serving=Decimal("0.4"),
        brand=None,
        source=source,
        external_id=external_id,
    )


def test_save_inserts_and_returns_with_id(tmp_path):
    repo = _repo(tmp_path)
    saved = repo.save(_sample())
    assert saved.id  # uuid populated
    assert saved.name == "Greek Yogurt"
    assert saved.calories_per_serving == 59


def test_find_by_external_id_returns_existing(tmp_path):
    repo = _repo(tmp_path)
    saved = repo.save(_sample(external_id="abc"))
    found = repo.find_by_external_id("usda", "abc")
    assert found is not None
    assert found.id == saved.id


def test_save_dedupes_on_source_external_id(tmp_path):
    """Saving the same (source, external_id) twice updates rather than duplicates."""
    repo = _repo(tmp_path)
    first = repo.save(_sample(external_id="dup"))
    again = repo.save(_sample(external_id="dup"))
    assert again.id == first.id  # same row reused

    # Updating fields on the duplicate save should overwrite.
    updated = CatalogIngredient(
        id="", name="Greek Yogurt", serving_label="227g",
        calories_per_serving=134, brand=None, source="usda", external_id="dup",
    )
    saved = repo.save(updated)
    assert saved.id == first.id
    assert saved.calories_per_serving == 134
    assert saved.serving_label == "227g"


def test_save_disambiguates_duplicate_names(tmp_path):
    """If two sources return the same name, both are saved (with disambiguating suffix)."""
    repo = _repo(tmp_path)
    a = repo.save(_sample(source="usda", external_id="aaa"))
    b = repo.save(_sample(source="openfoodfacts", external_id="bbb"))
    assert a.id != b.id
    assert a.name == "Greek Yogurt"
    assert "Greek Yogurt" in b.name
    assert b.name != a.name  # had to disambiguate


def test_search_by_name(tmp_path):
    repo = _repo(tmp_path)
    repo.save(_sample(name="Greek Yogurt", external_id="g1"))
    repo.save(_sample(name="Whole Milk Yogurt", external_id="g2"))
    repo.save(_sample(name="Cottage Cheese", external_id="c1"))

    yogurts = repo.search_by_name("yogurt", limit=10)
    assert len(yogurts) == 2
    assert all("yogurt" in y.name.lower() for y in yogurts)


def test_find_by_id_roundtrip(tmp_path):
    repo = _repo(tmp_path)
    saved = repo.save(_sample())
    loaded = repo.find_by_id(saved.id)
    assert loaded is not None
    assert loaded.calories_per_serving == saved.calories_per_serving
    assert loaded.protein_per_serving == saved.protein_per_serving


def test_find_by_id_missing_returns_none(tmp_path):
    repo = _repo(tmp_path)
    assert repo.find_by_id("nope") is None
