-- Initial database schema for meal planning app
-- Multi-user support with Clean Architecture principles

-- Users table for multi-user support
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    current_weight DECIMAL(5,2),
    body_fat_percentage DECIMAL(4,2),
    target_weight_loss_per_week DECIMAL(3,2),
    daily_calorie_target INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Recipes table with user ownership
CREATE TABLE IF NOT EXISTS recipes (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    base_servings INTEGER NOT NULL,
    calories_per_serving INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Ingredients table (normalized)
CREATE TABLE IF NOT EXISTS ingredients (
    id TEXT PRIMARY KEY,
    recipe_id TEXT NOT NULL,
    name TEXT NOT NULL,
    quantity DECIMAL(10,2) NOT NULL,
    unit TEXT NOT NULL,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

-- User inventory
CREATE TABLE IF NOT EXISTS inventory (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    ingredient_name TEXT NOT NULL,
    quantity DECIMAL(10,2) NOT NULL,
    unit TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, ingredient_name, unit)
);

-- Daily calorie logs for flexible dieting
CREATE TABLE IF NOT EXISTS daily_calorie_logs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    date DATE NOT NULL,
    target_calories INTEGER NOT NULL,
    consumed_calories INTEGER DEFAULT 0,
    banked_calories INTEGER DEFAULT 0,
    protein_grams DECIMAL(6,2),
    carb_grams DECIMAL(6,2),
    fat_grams DECIMAL(6,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, date)
);

-- Weekly calorie plans
CREATE TABLE IF NOT EXISTS weekly_calorie_plans (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    week_start_date DATE NOT NULL,
    weekly_calorie_target INTEGER NOT NULL,
    daily_targets TEXT NOT NULL, -- JSON array of 7 daily targets
    special_events TEXT, -- JSON array of special event descriptions
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, week_start_date)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_recipes_user_id ON recipes(user_id);
CREATE INDEX IF NOT EXISTS idx_ingredients_recipe_id ON ingredients(recipe_id);
CREATE INDEX IF NOT EXISTS idx_inventory_user_id ON inventory(user_id);
CREATE INDEX IF NOT EXISTS idx_daily_logs_user_date ON daily_calorie_logs(user_id, date);
CREATE INDEX IF NOT EXISTS idx_weekly_plans_user_date ON weekly_calorie_plans(user_id, week_start_date);

-- (Previously: BEFORE-UPDATE triggers to bump updated_at. Removed for
-- Postgres compatibility — every UPDATE in the repository code already
-- writes updated_at = CURRENT_TIMESTAMP explicitly, so the triggers are
-- redundant.)
