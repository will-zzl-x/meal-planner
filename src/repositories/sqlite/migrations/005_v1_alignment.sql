-- Phase A2: align migrations with the V1 repository code.
-- 1. Replace migration 001's slim per-recipe `ingredients` table with a normalized
--    nutrition catalog, and introduce `recipe_ingredients` as the join table.
-- 2. Add the `instructions` column the recipe repository already writes.
-- 3. Add password_hash + is_planner to users for the V1 multi-account auth.

-- The slim `ingredients` table (migration 001) and the catalog `ingredients`
-- table (this migration) share the same name but a different shape. Migration-
-- built databases were never used in production (production code ran on the
-- legacy schema.sql), so it is safe to drop and recreate here.
DROP TABLE IF EXISTS ingredients;

CREATE TABLE IF NOT EXISTS ingredients (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    calories_per_100g INTEGER,
    protein_per_100g DECIMAL(5,2),
    carbs_per_100g DECIMAL(5,2),
    fat_per_100g DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
    id TEXT PRIMARY KEY,
    recipe_id TEXT NOT NULL,
    ingredient_id TEXT NOT NULL,
    quantity DECIMAL(10,2) NOT NULL,
    unit TEXT NOT NULL,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id),
    UNIQUE(recipe_id, ingredient_id)
);

ALTER TABLE recipes ADD COLUMN instructions TEXT;
ALTER TABLE users ADD COLUMN password_hash TEXT;
ALTER TABLE users ADD COLUMN is_planner INTEGER DEFAULT 0;  -- SQLite has no real BOOLEAN

CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe_id ON recipe_ingredients(recipe_id);
CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_ingredient_id ON recipe_ingredients(ingredient_id);
CREATE INDEX IF NOT EXISTS idx_ingredients_name ON ingredients(name);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- weekly_calorie_plans was created in migration 001 with a single `daily_targets`
-- JSON column, but the SQLiteCalorieTrackingRepository writes seven per-day
-- columns. Recreate the table to match the repository's actual shape.
DROP TABLE IF EXISTS weekly_calorie_plans;
CREATE TABLE weekly_calorie_plans (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    week_start_date DATE NOT NULL,
    weekly_calorie_target INTEGER NOT NULL,
    monday_target INTEGER,
    tuesday_target INTEGER,
    wednesday_target INTEGER,
    thursday_target INTEGER,
    friday_target INTEGER,
    saturday_target INTEGER,
    sunday_target INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, week_start_date)
);
CREATE INDEX IF NOT EXISTS idx_weekly_plans_user_week
    ON weekly_calorie_plans(user_id, week_start_date);
