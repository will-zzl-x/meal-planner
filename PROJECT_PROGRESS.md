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
  Recipe cards show pantry coverage ("8/11 in pantry") with a
  "Missing from pantry" list inside.
- Auto-seeded recipes: 13 starter recipes are added when a household is
  registered, and immediately auto-backfilled against the food databases
  so calorie figures are real on day one.
- Weekly plan: planner schedules recipes to (day, meal_type) slots.
- Pantry: items can be linked to catalog entries via search; planner-only
  Quick check-in mode for fast tap-through review (Have it / Out /
  Adjust per row); "Last reviewed N days ago" caption.
- Grocery list: weekly plan minus pantry. Catalog-keyed subtraction
  with unit conversion (1 lb pantry chicken cancels 200g recipe demand);
  legacy name+unit fallback for items without catalog refs. Stale-pantry
  banner reminds the user to do a check-in if the pantry is >3 days old.
- Today: per-user food log; tick planned meals; log off-plan via the same
  food picker (or a free-text "quick log" for things not in any DB);
  calorie progress bar against daily target.
- Profile: body-composition fields drive a per-user daily calorie target.

### Schema state
Migrations 001–011 applied. Most recent ones:
- 008 — recipe metadata (notes, tier) and per-ingredient store
- 009 — widened `ingredients` catalog with serving_label + per-serving
  nutrition + (source, external_id) for caching real DB hits
- 010 — `recipe_ingredients.display_name` so the user-typed ingredient
  name survives a backfill (was being overwritten by catalog name)
- 011 — `inventory.catalog_ingredient_id` so pantry rows can link to
  the same catalog rows recipe ingredients use, enabling exact
  coverage matching

### Test coverage
226 tests in `src/`, all passing at HEAD. Coverage:
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
- Task 15: Refresh of this document.

### V2 — Pantry coverage & fast check-in (11 tasks, 11 commits)
- V2-1: Migration 011 — `inventory.catalog_ingredient_id`. Pantry
  rows can now reference the same catalog rows recipes use.
- V2-2: `InventoryItem` + repo carry the new column on every read /
  write / upsert path. Repo tests extended.
- V2-3: Pantry add form gets a "Link to a food database entry"
  expander above the existing form. Quantity and unit stay in
  natural shopping units (lb, cup, oz, g) — the catalog ref is
  metadata for matching, not the user's display unit.
- V2-4: New `pantry_backfiller.py` + `scripts/backfill_pantry.py`
  CLI for retroactive resolution of legacy pantry rows.
- V2-5: New `pantry_coverage_service.py` — answers "how much of
  this recipe do I already have?" via catalog id matching with
  unit conversion. Hard-coded staples list (toggleable).
- V2-6: Recipe cards show a coverage chip in the header
  ("8/11 in pantry") and a "Missing from pantry" / "All ingredients
  in pantry" block inside.
- V2-7: Recipes page filter row — coverage threshold, treat-staples
  toggle, sort-by-coverage. Recipes with no catalog-backed lines
  are exempt from the filter so brand-new households still see
  their seeds.
- V2-8: Pantry page Quick check-in mode. Each row gets Have it /
  Out / Adjust controls; a "Last reviewed: N days ago" caption
  drives the user toward keeping inventory current.
- V2-9: Stale-pantry banner on the Grocery list page.
- V2-10: Grocery list service uses catalog-keyed subtraction with
  unit conversion. "1 lb chicken" in pantry now correctly cancels
  200g of recipe demand. Legacy (name, unit) match preserved as
  fallback when either side lacks a catalog ref.
- V2-11: This update.

Test count after V2: 226 (up from 205 at the start of V2).

---

## Outstanding (V3 candidates, in rough priority order)

1. **First end-to-end click-through on iPhone Safari.** Still
   code-review only — real device pass is the highest-value next
   step.
2. **Macros breakdown (P/C/F) on Today.** Deferred from overnight
   Task 10 — needs either macros stored on `food_log_entries` at
   log time or N catalog joins per render.
3. **Short human-friendly invite codes.** UUID is unguessable but
   ugly to dictate over a phone.
4. **Bias picker results toward the household's already-cached
   catalog.** Avoids re-fetching popular items and visually flags
   "you've used this before."
5. **Recipe scaling on add-to-meal-plan** (e.g., "use 2x the recipe
   for this slot"). Service exists; UI doesn't.
6. **Per-household configurable staples list.** V2 hard-codes
   salt/oil/pepper; V3 should let each household tune it.
7. **Pantry expiration tracking.** The domain model has
   `expiration_date`; the schema doesn't store it. Useful for
   "use this up before it goes bad" recipe nudges.
8. **Onboarding banner** for the first user, pointing at Add a recipe
   and Pantry check-in.
9. **Forgot-password / account deletion.** Out of MVP scope; needed
   before public launch.
10. **Native or React Native mobile app.** Streamlit is fine for the
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
