"""Pure-helper tests for the Today view."""
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from web.views.today import _fmt_servings, _progress_text


def test_progress_text_under_target():
    assert _progress_text(1500, 2000) == "1500 / 2000 cal · 75%"


def test_progress_text_at_target():
    assert _progress_text(2000, 2000) == "2000 / 2000 cal · 100%"


def test_progress_text_over_target():
    assert _progress_text(2200, 2000) == "2200 / 2000 cal · 110% (over by 200)"


def test_progress_text_zero_target_does_not_crash():
    """Defensive: target=0 shouldn't divide-by-zero. The UI guards against
    rendering this case but the helper should still be safe."""
    out = _progress_text(500, 0)
    assert "500" in out and "0%" in out


# ------------------------------------------------- _fmt_servings

def test_fmt_servings_strips_trailing_zeros():
    assert _fmt_servings(Decimal("1.0")) == "1"
    assert _fmt_servings(Decimal("2.50")) == "2.5"


def test_fmt_servings_preserves_meaningful_decimals():
    assert _fmt_servings(Decimal("1.5")) == "1.5"
    assert _fmt_servings(Decimal("0.25")) == "0.25"


def test_fmt_servings_integer_shows_no_dot():
    assert _fmt_servings(Decimal("3")) == "3"
