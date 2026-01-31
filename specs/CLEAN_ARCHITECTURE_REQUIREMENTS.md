# Clean Architecture Requirements (EARS Format)
# Meal Planning App - Strict Architectural Principles

## Clean Architecture Hierarchy
**EARS-CLEAN-001**: WHEN organizing source code, THE SYSTEM SHALL enforce strict dependency flow: src/web → src/repositories → src/core with no reverse dependencies.

**EARS-CLEAN-002**: WHERE business logic exists, THE SYSTEM SHALL place it exclusively in src/core with no external dependencies.

**EARS-CLEAN-003**: WHEN data access is required, THE SYSTEM SHALL implement it in src/repositories using interfaces defined in src/core.

## Naming Conventions
**EARS-CLEAN-004**: WHEN defining interfaces, THE SYSTEM SHALL prefix all interface names with 'I' (e.g., IRecipeRepository).

**EARS-CLEAN-005**: WHERE data models are created, THE SYSTEM SHALL use singular naming (Recipe, not Recipes).

**EARS-CLEAN-006**: WHEN creating test files, THE SYSTEM SHALL suffix all test files with '_test.py' for clear identification.

## Documentation Automation
**EARS-CLEAN-007**: WHEN syncing documentation, THE SYSTEM SHALL exclude tests/ and specs/ folders to maintain focus on production architecture.

**EARS-CLEAN-008**: WHERE future updates occur, THE SYSTEM SHALL target Windows environment exclusively, not Ubuntu development environment.
