# Clean Architecture Structure & Governance
# Meal Planning App - Strict Architectural Principles

## 🏗️ Clean Architecture Hierarchy

### Dependency Flow (STRICT - No Violations)
```
src/web (UI Layer)
    ↓ depends on
src/repositories (Data Access Layer) 
    ↓ depends on
src/core (Business Logic Layer)
    ↓ depends on
Nothing (Pure Business Logic)
```

### Layer Responsibilities

#### src/core/ - Business Logic (Inner Layer)
**WHAT IT CONTAINS:**
- Domain models (Recipe, Ingredient, User)
- Business logic services (RecipeScaler, IngredientAggregator)
- Interface definitions (IRecipeRepository, IUserRepository)
- Security validation (input sanitization, business rules)

**DEPENDENCIES:** None - Pure business logic
**RULE:** Cannot import from src/repositories or src/web

#### src/repositories/ - Data Access (Middle Layer)
**WHAT IT CONTAINS:**
- Repository implementations (SqliteRecipeRepository)
- Database schemas and migrations
- Data persistence logic
- External service integrations

**DEPENDENCIES:** Only src/core interfaces
**RULE:** Cannot import from src/web, implements interfaces from src/core

#### src/web/ - UI Layer (Outer Layer)
**WHAT IT CONTAINS:**
- Streamlit pages and components
- CLI interfaces
- Request/response handling
- User session management

**DEPENDENCIES:** src/core and src/repositories
**RULE:** Can import from any layer, but no other layer imports from web

## 📝 Naming Conventions (MANDATORY)

### Interfaces
- **Format:** I + PascalCase + Repository/Service
- **Examples:** `IRecipeRepository`, `IUserService`, `ICalorieTracker`
- **Rule:** All interfaces MUST start with 'I'

### Models
- **Format:** Singular PascalCase
- **Examples:** `Recipe` (not Recipes), `User` (not Users), `Ingredient` (not Ingredients)
- **Rule:** Always singular, represents single entity

### Services
- **Format:** PascalCase + Service/Manager/Handler
- **Examples:** `RecipeScaler`, `IngredientAggregator`, `CalorieCalculator`
- **Rule:** Descriptive action-based naming

### Test Files
- **Format:** [module_name]_test.py
- **Examples:** `recipe_scaler_test.py`, `user_repository_test.py`
- **Rule:** All test files MUST end with '_test.py'

### Database Tables
- **Format:** snake_case, plural
- **Examples:** `recipes`, `users`, `daily_calorie_logs`
- **Rule:** Database uses snake_case, models use PascalCase

## 🔄 Development Workflow (ENFORCED)

### 1. Requirements First (EARS Format)
- All features start with EARS requirements in specs/
- No code without corresponding requirement
- Requirements reviewed before implementation

### 2. Design Before Code
- Technical design in .kiro/steering/technical.md
- Architecture decisions in .kiro/steering/architecture.md
- Interface definitions before implementations

### 3. Clean Architecture Compliance
- Business logic in src/core/ only
- No reverse dependencies allowed
- Interface-driven development

### 4. Testing Strategy
- Unit tests for src/core/ services
- Integration tests for src/repositories/
- End-to-end tests for src/web/
- All tests follow naming convention

## 🚨 Architecture Violations (FORBIDDEN)

### Dependency Violations
```python
# ❌ FORBIDDEN - Core depending on outer layers
from src.repositories import SqliteRecipeRepository  # In src/core/

# ❌ FORBIDDEN - Repository depending on web
from src.web import streamlit_helpers  # In src/repositories/

# ✅ ALLOWED - Outer layers depending on inner
from src.core import IRecipeRepository  # In src/repositories/
```

### Naming Violations
```python
# ❌ FORBIDDEN - Interface without 'I' prefix
class RecipeRepository(ABC):  # Should be IRecipeRepository

# ❌ FORBIDDEN - Plural model name
class Recipes:  # Should be Recipe

# ❌ FORBIDDEN - Wrong test file naming
recipe_tests.py  # Should be recipe_test.py
```

## 📊 Quality Gates

### Code Review Checklist
- [ ] No dependency violations (use import analysis)
- [ ] All interfaces start with 'I'
- [ ] All models are singular
- [ ] All test files end with '_test.py'
- [ ] Business logic only in src/core/
- [ ] No database calls in src/core/

### Automated Checks
- Dependency analysis on every commit
- Naming convention validation
- Test coverage requirements
- Architecture compliance verification

## 🎯 Benefits of This Structure

### Testability
- Mock any layer independently
- Business logic testable without database
- UI testable without external dependencies

### Maintainability
- Clear separation of concerns
- Easy to locate functionality
- Consistent naming across codebase

### Scalability
- Add new features without breaking existing code
- Swap implementations without changing business logic
- Team can work on different layers simultaneously

### Professional Standards
- Industry-standard Clean Architecture
- Enterprise-grade development practices
- Easy onboarding for new developers

This structure ensures the codebase remains maintainable, testable, and scalable as the application grows from prototype to production.
