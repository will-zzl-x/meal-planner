-- Meal Planning App Database Schema
-- Based on successful open source nutrition & meal planning apps
-- SQLite with multi-user support and flexible dieting features

-- Users table for multi-user support
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User profiles for body composition and calorie targets
CREATE TABLE user_profiles (
    user_id TEXT PRIMARY KEY,
    current_weight DECIMAL(5,2),
    body_fat_percentage DECIMAL(4,2),
    target_weight_loss_per_week DECIMAL(3,2),
    daily_calorie_target INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Base ingredients (normalized nutrition data)
CREATE TABLE ingredients (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    calories_per_100g INTEGER,
    protein_per_100g DECIMAL(5,2),
    carbs_per_100g DECIMAL(5,2),
    fat_per_100g DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Recipes with user ownership
CREATE TABLE recipes (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    base_servings INTEGER NOT NULL,
    calories_per_serving INTEGER,
    protein_per_serving DECIMAL(5,2),
    carbs_per_serving DECIMAL(5,2),
    fat_per_serving DECIMAL(5,2),
    instructions TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Recipe ingredients (many-to-many with quantities)
CREATE TABLE recipe_ingredients (
    id TEXT PRIMARY KEY,
    recipe_id TEXT NOT NULL,
    ingredient_id TEXT NOT NULL,
    quantity DECIMAL(10,2) NOT NULL,
    unit TEXT NOT NULL,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id),
    UNIQUE(recipe_id, ingredient_id)
);

-- User inventory
CREATE TABLE inventory (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    ingredient_id TEXT NOT NULL,
    quantity DECIMAL(10,2) NOT NULL,
    unit TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id),
    UNIQUE(user_id, ingredient_id, unit)
);

-- Weekly calorie plans for flexible dieting
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
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, week_start_date)
);

-- Daily calorie logs for tracking
CREATE TABLE daily_calorie_logs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    date DATE NOT NULL,
    target_calories INTEGER NOT NULL,
    consumed_calories INTEGER DEFAULT 0,
    protein_grams DECIMAL(5,2) DEFAULT 0,
    carb_grams DECIMAL(5,2) DEFAULT 0,
    fat_grams DECIMAL(5,2) DEFAULT 0,
    banked_calories INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, date)
);

-- Meal plans (which recipes to make on which days)
CREATE TABLE meal_plans (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    recipe_id TEXT NOT NULL,
    planned_date DATE NOT NULL,
    planned_servings INTEGER NOT NULL,
    meal_type TEXT CHECK(meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

-- Store profiles for package sizing
CREATE TABLE store_profiles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Store-specific ingredient sizing
CREATE TABLE store_ingredient_sizes (
    id TEXT PRIMARY KEY,
    store_profile_id TEXT NOT NULL,
    ingredient_id TEXT NOT NULL,
    package_size DECIMAL(10,2) NOT NULL,
    package_unit TEXT NOT NULL,
    typical_price DECIMAL(8,2),
    FOREIGN KEY (store_profile_id) REFERENCES store_profiles(id) ON DELETE CASCADE,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id),
    UNIQUE(store_profile_id, ingredient_id, package_unit)
);

-- Indexes for performance
CREATE INDEX idx_recipes_user_id ON recipes(user_id);
CREATE INDEX idx_recipe_ingredients_recipe_id ON recipe_ingredients(recipe_id);
CREATE INDEX idx_inventory_user_id ON inventory(user_id);
CREATE INDEX idx_daily_logs_user_date ON daily_calorie_logs(user_id, date);
CREATE INDEX idx_meal_plans_user_date ON meal_plans(user_id, planned_date);
CREATE INDEX idx_weekly_plans_user_week ON weekly_calorie_plans(user_id, week_start_date);
