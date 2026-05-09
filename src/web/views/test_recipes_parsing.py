"""Unit tests for the ingredient-parsing helper used by the Recipes view."""
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from web.views.recipes import _parse_ingredients


def test_parses_simple_two_line_block():
    ingredients = _parse_ingredients("chicken breast, 6, oz\nrice, 1, cup")
    assert len(ingredients) == 2
    assert ingredients[0].name == "chicken breast"
    assert ingredients[0].quantity == Decimal("6")
    assert ingredients[0].unit == "oz"


def test_skips_blank_lines():
    ingredients = _parse_ingredients("\n\nrice, 1, cup\n\n")
    assert len(ingredients) == 1


def test_rejects_wrong_segment_count():
    with pytest.raises(ValueError, match="Line 1: expected"):
        _parse_ingredients("chicken breast, 6")


def test_rejects_non_numeric_quantity():
    with pytest.raises(ValueError, match="quantity 'lots'"):
        _parse_ingredients("chicken breast, lots, oz")


def test_rejects_unit_with_invalid_characters():
    # The validator is permissive about unit names but still rejects characters
    # that could carry SQL or HTML payloads.
    with pytest.raises(ValueError, match="Line 1"):
        _parse_ingredients("chicken breast, 6, ;DROP TABLE")


def test_empty_input_raises():
    with pytest.raises(ValueError, match="at least one ingredient"):
        _parse_ingredients("")
