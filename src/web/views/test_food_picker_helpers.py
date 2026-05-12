"""Pure-helper tests for the food picker and recipes view.

Streamlit-rendering parts can't be exercised without a browser, but the
data-shaping helpers are plain functions and can be tested directly.
"""
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.domain.models import CatalogIngredient
from web.views.food_picker import _parse_servings
from web.views.recipes import (
    _DraftIngredient,
    _drafts_to_ingredients,
    _fmt_decimal,
    _format_coverage_chip,
    _per_serving_total,
)


# ------------------------------------------------- _parse_servings

def test_parse_servings_accepts_integers_and_decimals():
    assert _parse_servings("1") == Decimal("1")
    assert _parse_servings("1.5") == Decimal("1.5")
    assert _parse_servings("0.25") == Decimal("0.25")


def test_parse_servings_strips_whitespace():
    assert _parse_servings("  2  ") == Decimal("2")


def test_parse_servings_rejects_zero_and_negatives():
    assert _parse_servings("0") is None
    assert _parse_servings("-1") is None


def test_parse_servings_rejects_non_numeric():
    assert _parse_servings("abc") is None
    assert _parse_servings("") is None
    assert _parse_servings(None) is None  # type: ignore[arg-type]


# ------------------------------------------------- _drafts_to_ingredients

def _draft(name: str = "Chicken Breast", servings: str = "1.5",
           store: str | None = None) -> _DraftIngredient:
    catalog = CatalogIngredient(
        id="cat-1", name=name, serving_label="100g",
        calories_per_serving=165, brand=None, source="usda", external_id="x",
    )
    return _DraftIngredient(catalog, Decimal(servings), store)


def test_drafts_to_ingredients_preserves_store():
    """Regression test: picker-built ingredients used to drop the store
    field, breaking grocery routing for picker-saved recipes."""
    drafts = [
        _draft(name="Chicken", store="Costco"),
        _draft(name="Rice", store=None),
    ]
    ingredients = _drafts_to_ingredients(drafts)
    assert ingredients[0].store == "Costco"
    assert ingredients[1].store is None


def test_drafts_to_ingredients_populates_catalog_ref():
    drafts = [_draft()]
    [ing] = _drafts_to_ingredients(drafts)
    assert ing.catalog_ingredient_id == "cat-1"
    assert ing.servings == Decimal("1.5")
    # quantity mirrors servings on picker-built rows so legacy consumers
    # see something sensible too.
    assert ing.quantity == Decimal("1.5")
    assert ing.unit == "100g"


# ------------------------------------------------- _per_serving_total

def test_per_serving_total_divides_correctly():
    drafts = [_draft(servings="2")]   # 2 × 165 = 330 cal
    drafts.append(_draft(servings="1"))  # +165 = 495 total
    assert _per_serving_total(drafts, 3) == 165


def test_per_serving_total_zero_servings_returns_zero():
    drafts = [_draft(servings="2")]
    assert _per_serving_total(drafts, 0) == 0


# ------------------------------------------------- _fmt_decimal

def test_fmt_decimal_strips_trailing_zeros():
    assert _fmt_decimal(Decimal("1.0")) == "1"
    assert _fmt_decimal(Decimal("2.50")) == "2.5"


def test_fmt_decimal_preserves_meaningful_decimals():
    assert _fmt_decimal(Decimal("1.5")) == "1.5"
    assert _fmt_decimal(Decimal("0.25")) == "0.25"


def test_fmt_decimal_integer_shows_no_dot():
    assert _fmt_decimal(Decimal("3")) == "3"


# ------------------------------------------------- _format_coverage_chip

def _coverage(have: int, total: int):
    """Build a CoverageReport-shaped object with a known have/total ratio."""
    from core.services.pantry_coverage_service import CoverageLine, CoverageReport
    lines = []
    for _ in range(have):
        lines.append(CoverageLine(ingredient_name="x", status="have"))
    for _ in range(total - have):
        lines.append(CoverageLine(ingredient_name="x", status="missing"))
    return CoverageReport(lines=lines)


def test_format_coverage_chip_partial():
    assert _format_coverage_chip(_coverage(8, 11)) == "8/11 in pantry"


def test_format_coverage_chip_all():
    assert _format_coverage_chip(_coverage(5, 5)) == "all in pantry"


def test_format_coverage_chip_no_catalog_data_is_blank():
    """Recipes with zero catalog-backed lines (legacy) get no chip — the
    ratio would be misleading."""
    assert _format_coverage_chip(_coverage(0, 0)) == ""
