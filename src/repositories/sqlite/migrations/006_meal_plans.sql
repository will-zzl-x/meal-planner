-- Slice 4: persist the household's weekly meal plan.
-- Each row is one (recipe, day, meal-type) entry. The same recipe can appear
-- multiple times in the same week (e.g. Monday lunch and Wednesday lunch);
-- (planned_date, recipe_id, meal_type) is unique within a household.
CREATE TABLE IF NOT EXISTS meal_plans (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL,
    recipe_id TEXT NOT NULL,
    planned_date DATE NOT NULL,
    planned_servings INTEGER NOT NULL,
    meal_type TEXT NOT NULL CHECK(meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (household_id) REFERENCES households(id) ON DELETE CASCADE,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    UNIQUE(household_id, planned_date, recipe_id, meal_type)
);

CREATE INDEX IF NOT EXISTS idx_meal_plans_household_date
    ON meal_plans(household_id, planned_date);
