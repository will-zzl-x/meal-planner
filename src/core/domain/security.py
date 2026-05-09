"""
Security validation utilities for meal planning app.
Implements input validation and sanitization per security requirements.
"""
import re
from decimal import Decimal, InvalidOperation
from typing import List, Optional

# Security constants
# Allow letters, digits, whitespace, and common cooking-name punctuation.
# Excludes characters that could carry SQL or HTML payloads (`;`, `<`, `>`,
# `"`, `\`, backticks).
ALLOWED_INGREDIENT_CHARS = re.compile(r"^[\w\s\-,.()+&/'%*~]+$")
MAX_INGREDIENT_NAME_LENGTH = 100
MAX_RECIPE_NAME_LENGTH = 200
# Units are validated permissively rather than against a whitelist: real cooking
# uses many unit names (thigh, pack, sprig, can, lemon, ...) and forcing them
# into a fixed list rejects perfectly reasonable input. Same character-class
# protections (no quotes, semicolons, etc.) remain.
ALLOWED_UNIT_CHARS = re.compile(r'^[a-zA-Z0-9\s\-_./]+$')
MAX_UNIT_LENGTH = 30

class SecurityValidationError(Exception):
    """Raised when security validation fails."""
    pass

def validate_ingredient_name(name: str) -> str:
    """Validate and sanitize ingredient name."""
    if not name or not isinstance(name, str):
        raise SecurityValidationError("Ingredient name is required")
    
    name = name.strip()
    
    if len(name) > MAX_INGREDIENT_NAME_LENGTH:
        raise SecurityValidationError(f"Ingredient name too long (max {MAX_INGREDIENT_NAME_LENGTH} chars)")
    
    if not ALLOWED_INGREDIENT_CHARS.match(name):
        raise SecurityValidationError("Ingredient name contains invalid characters")
    
    return name

def validate_recipe_name(name: str) -> str:
    """Validate and sanitize recipe name."""
    if not name or not isinstance(name, str):
        raise SecurityValidationError("Recipe name is required")
    
    name = name.strip()
    
    if len(name) > MAX_RECIPE_NAME_LENGTH:
        raise SecurityValidationError(f"Recipe name too long (max {MAX_RECIPE_NAME_LENGTH} chars)")
    
    if not ALLOWED_INGREDIENT_CHARS.match(name):
        raise SecurityValidationError("Recipe name contains invalid characters")
    
    return name

def validate_quantity(quantity) -> Decimal:
    """Validate and convert quantity to secure Decimal."""
    try:
        if isinstance(quantity, str):
            # Remove any non-numeric characters except decimal point
            cleaned = re.sub(r'[^\d.]', '', quantity)
            decimal_qty = Decimal(cleaned)
        else:
            decimal_qty = Decimal(str(quantity))
        
        if decimal_qty < 0:
            raise SecurityValidationError("Quantity cannot be negative")
        
        if decimal_qty > Decimal('10000'):  # Reasonable upper limit
            raise SecurityValidationError("Quantity too large")
        
        return decimal_qty
    
    except (InvalidOperation, ValueError):
        raise SecurityValidationError("Invalid quantity format")

def validate_unit(unit: str) -> str:
    """Validate unit (permissive: any alphanumeric/space/hyphen/dot/slash up to 30 chars)."""
    if not unit or not isinstance(unit, str):
        raise SecurityValidationError("Unit is required")

    unit = unit.strip().lower()

    if len(unit) > MAX_UNIT_LENGTH:
        raise SecurityValidationError(f"Unit too long (max {MAX_UNIT_LENGTH} chars)")

    if not ALLOWED_UNIT_CHARS.match(unit):
        raise SecurityValidationError("Unit contains invalid characters")

    return unit

def validate_servings(servings) -> int:
    """Validate serving count."""
    try:
        servings_int = int(servings)
        if servings_int <= 0:
            raise SecurityValidationError("Servings must be positive")
        if servings_int > 100:  # Reasonable upper limit
            raise SecurityValidationError("Too many servings")
        return servings_int
    except (ValueError, TypeError):
        raise SecurityValidationError("Invalid servings format")

def validate_calories(calories) -> int:
    """Validate calories per serving."""
    try:
        calories_int = int(calories)
        if calories_int < 0:
            raise SecurityValidationError("Calories cannot be negative")
        if calories_int > 5000:  # Reasonable upper limit per serving
            raise SecurityValidationError("Calories per serving too high")
        return calories_int
    except (ValueError, TypeError):
        raise SecurityValidationError("Invalid calories format")
