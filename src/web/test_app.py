"""
Smoke tests for the Streamlit app module.

Streamlit forms can't be exercised without a running Streamlit runtime, so the
real interactive flows are tested via the AuthService unit tests. Here we
just confirm the module imports cleanly and exposes the expected entry points.
"""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_app_module_imports_cleanly():
    module = importlib.import_module("web.app")
    for attr in (
        "get_auth_service",
        "get_recipe_repo",
        "get_inventory_repo",
        "get_meal_plan_repo",
        "get_grocery_service",
        "render_login_form",
        "render_register_household_form",
        "render_register_member_form",
        "render_unauthenticated",
        "render_authenticated",
        "weekly_plan_page_entry",
        "grocery_list_page_entry",
        "main",
    ):
        assert hasattr(module, attr), f"app.py missing entry point: {attr}"
