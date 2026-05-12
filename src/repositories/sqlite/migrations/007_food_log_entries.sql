-- Slice 5: per-user food logging.
-- One row per (user, planned-meal-tick). Off-plan entries leave
-- meal_plan_entry_id NULL and require description + calories.
-- The UNIQUE(user_id, meal_plan_entry_id) constraint prevents double-ticking
-- the same planned slot; SQLite treats multiple NULLs as distinct, so any
-- number of off-plan entries per user/day are allowed.
CREATE TABLE IF NOT EXISTS food_log_entries (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    log_date DATE NOT NULL,
    meal_plan_entry_id TEXT,
    description TEXT,
    calories INTEGER NOT NULL,
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (meal_plan_entry_id) REFERENCES meal_plans(id) ON DELETE CASCADE,
    UNIQUE(user_id, meal_plan_entry_id)
);

CREATE INDEX IF NOT EXISTS idx_food_log_entries_user_date
    ON food_log_entries(user_id, log_date);
