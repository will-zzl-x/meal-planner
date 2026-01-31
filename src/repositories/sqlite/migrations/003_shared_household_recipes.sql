-- Update recipes table for household sharing
-- Change from user_id to household_id for shared recipe access

-- Update recipes table to use household_id instead of user_id
-- Note: SQLite doesn't support DROP COLUMN, so we'll recreate the table

-- Create new recipes table with household_id
CREATE TABLE IF NOT EXISTS recipes_new (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL,
    name TEXT NOT NULL,
    base_servings INTEGER NOT NULL,
    calories_per_serving INTEGER NOT NULL,
    created_by_user_id TEXT NOT NULL, -- Track who created it
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (household_id) REFERENCES households(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Copy existing data if any (transform user_id to household_id)
INSERT INTO recipes_new (id, household_id, name, base_servings, calories_per_serving, created_by_user_id, created_at, updated_at)
SELECT r.id, u.household_id, r.name, r.base_servings, r.calories_per_serving, r.user_id, r.created_at, r.updated_at
FROM recipes r
JOIN users u ON r.user_id = u.id
WHERE u.household_id IS NOT NULL;

-- Drop old table and rename new one
DROP TABLE IF EXISTS recipes;
ALTER TABLE recipes_new RENAME TO recipes;

-- Update ingredients table foreign key (no change needed, still references recipe_id)

-- Update indexes
DROP INDEX IF EXISTS idx_recipes_user_id;
CREATE INDEX IF NOT EXISTS idx_recipes_household_id ON recipes(household_id);
CREATE INDEX IF NOT EXISTS idx_recipes_created_by ON recipes(created_by_user_id);

-- Update trigger
DROP TRIGGER IF EXISTS update_recipes_timestamp;
CREATE TRIGGER IF NOT EXISTS update_recipes_timestamp 
    AFTER UPDATE ON recipes
    BEGIN
        UPDATE recipes SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;
