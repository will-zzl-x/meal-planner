# Meal Planner — Project Progress

A Python/Streamlit multi-account household meal-planning app. One designated
planner per household; other members are read-only and can log their own
intake. Built around real food databases (USDA + Open Food Facts) so
calories are exact, not estimated.

---

## Current state (May 2026)

The MVP is functionally complete and on branch `claude/review-recent-changes-JVO0f`.

### What works end-to-end
- Auth: email + password, register-household / join-household via invite code,
  PBKDF2 password hashing.
- Households: shared recipes, shared pantry, planner-only edits.
- Recipes: build via search-and-pick from USDA / Open Food Facts; calories
  computed live from picked ingredients × servings; per-ingredient store
  routing preserved; manual fallback for items the databases don't cover.
- Auto-seeded recipes: 13 starter recipes are added when a household is
  registered, and immediately auto-backfilled against the food databases
  so calorie figures are real on day one.
- Weekly plan: planner schedules recipes to (day, meal_type) slots.
- Grocery list: weekly plan minus pantry, aggregated by ingredient.
- Today: per-user food log; tick planned meals; log off-plan via the same
  food picker (or a free-text "quick log" for things not in any DB);
  calorie progress bar against daily target.
- Profile: body-composition fields drive a per-user daily calorie target.

### Schema state
Migrations 001–010 applied. Most recent ones:
- 008 — recipe metadata (notes, tier) and per-ingredient store
- 009 — widened `ingredients` catalog with serving_label + per-serving
  nutrition + (source, external_id) for caching real DB hits
- 010 — `recipe_ingredients.display_name` so the user-typed ingredient
  name survives a backfill (was being overwritten by catalog name)

### Test coverage
205 tests in `src/`, all passing at HEAD. Coverage:
- All services have unit tests (auth, calorie calculator, food DB,
  grocery list, password hashing, recipe scaler, seed backfiller, etc).
- All SQLite repos have tests (households, users, recipes, meal plans,
  food log, inventory, ingredient catalog).
- View modules: pure helpers tested where extractable; Streamlit
  rendering itself can't be tested without a browser.

---

## Slice ledger

### Slice 7 — recipe editing
- IRecipeRepository.update + SQLite implementation.
- Recipe edit form (planner-only, pre-populated).
- Removed: estimator-based calorie path (replaced in 8b by exact
  catalog math).

### Slice 8a — real food search foundation
- Migration 009: widened `ingredients` table for cached external rows.
- `CatalogIngredient` domain model + `SQLiteIngredientCatalogRepository`.
- `FoodDatabaseService` rewritten: live USDA + Open Food Facts (sync,
  5-second timeout); offline sample DB as fallback; tests with mocked
  HTTP.

### Slice 8b — recipe form rewritten around the picker
- `Ingredient` model gains `catalog_ingredient_id` + `servings`.
- Recipe repo: catalog-backed paths in save/update/read.
- New `RecipeCalorieCalculator` service replaces the old estimator.
- New `web/views/food_picker.py` reusable widget; recipes view rebuilt
  around it.

### Slice 8c — Today food diary uses the picker
- `Today` page logs off-plan meals via the same picker (calories =
  servings × catalog calories).
- Free-text quick-log preserved as a fallback expander.

### Slice 8d — household page
- New `web/views/household.py`: shows household name, invite code,
  member list with planner/member roles.

### Slice 8e — auto-backfill
- New `core/services/seed_recipe_backfiller.py`: matches legacy
  free-text ingredients against the food DBs, converts units, persists
  the catalog reference. Idempotent.
- New `scripts/backfill_recipes.py` CLI tool.

### Overnight pass — fixes & polish (15 tasks, 13 commits)
- Task 1: Picker preserves the per-ingredient `store` field.
- Task 2: Migration 010 + repo wiring so user-typed ingredient names
  survive a backfill.
- Task 3: Backfill strips stale "[calories pending lookup]" markers
  from notes when calories are populated.
- Task 4: Calorie calculator shows the user's name, not the catalog
  display name.
- Task 5: Recipe scaler preserves catalog refs and store on scaling.
- Tasks 6+7: Picker shows "no results" feedback; result rows stack
  vertically on narrow screens.
- Task 8: Forms preserve user input on validation error.
- Task 9: Remove buttons widened for mobile tap targets.
- Task 10: Today page shows a calorie progress bar (macros deferred).
- Task 11: AuthService auto-runs the backfill after seeding starter
  recipes — new households see real calories on day one.
- Task 12: "Add manually" path in the picker for foods the databases
  don't cover.
- Task 13: Unit tests for view-helper pure functions.
- Task 14: Repository tests for food log, meal plans, inventory.
- Task 15: This document.

---

## Outstanding (V2 candidates, in rough priority order)

1. **First end-to-end click-through on iPhone Safari.** Code-review
   only so far; real device pass is the highest-value next step.
2. **Macros breakdown (P/C/F) on Today.** Deferred from Task 10 —
   needs either macros stored on `food_log_entries` at log time or
   N catalog joins per render.
3. **Short human-friendly invite codes.** UUID is unguessable but
   ugly to dictate over a phone.
4. **Bias picker results toward the household's already-cached
   catalog.** Avoids re-fetching popular items and visually flags
   "you've used this before."
5. **Recipe scaling on add-to-meal-plan** (e.g., "use 2x the recipe
   for this slot"). Service exists; UI doesn't.
6. **Onboarding banner** for the first user, pointing at Add a recipe.
7. **Forgot-password / account deletion.** Out of MVP scope; needed
   before public launch.
8. **Native or React Native mobile app.** Streamlit is fine for the
   self-host MVP but not a competitive paid product.

---

## Architecture overview

```
src/
├── core/                          # Inner layer (no I/O imports)
│   ├── domain/                    # Dataclasses + validation
│   ├── interfaces/                # Repository ABCs
│   └── services/                  # Business logic
├── repositories/sqlite/
│   ├── migrations/                # 001–010, applied at startup
│   └── *_repository.py            # SQLite implementations of ABCs
└── web/
    ├── app.py                     # Streamlit entry point + DI wiring
    └── views/                     # One module per page
```

Key design choices that influence ongoing work:
- Repos are constructed once via `@st.cache_resource` in `app.py` and
  passed into views as plain function args. Views never `import`
  repos directly.
- Catalog rows from real DBs are deduped on `(source, external_id)`.
- Ingredient names on each recipe row are preserved separately from
  the catalog row (migration 010), so backfill doesn't visibly rename
  ingredients.
- The food picker widget is reused everywhere a food has to be
  attached (recipes, food log) so UX stays consistent.

---

## Running

```bash
# Apply migrations + start the app
streamlit run src/web/app.py

# Run all tests
cd src && pytest -q

# Backfill an existing DB's recipes against USDA / OFF
python scripts/backfill_recipes.py --all-households
# or offline (sample DB only):
python scripts/backfill_recipes.py --all-households --offline
```

The DB file lives at `meal_planner.db` by default; override with the
`MEAL_PLANNER_DB` environment variable.
