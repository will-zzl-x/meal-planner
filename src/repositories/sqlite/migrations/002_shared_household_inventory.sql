-- Update inventory table for household sharing
-- Remove user_id foreign key constraint and make inventory global per household

-- Drop existing inventory table and recreate with household concept
DROP TABLE IF EXISTS inventory;

-- Create households table for grouping users
CREATE TABLE IF NOT EXISTS households (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Update users table to include household_id
ALTER TABLE users ADD COLUMN household_id TEXT REFERENCES households(id);

-- Recreate inventory table with household_id instead of user_id
CREATE TABLE IF NOT EXISTS inventory (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL,
    ingredient_name TEXT NOT NULL,
    quantity DECIMAL(10,2) NOT NULL,
    unit TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (household_id) REFERENCES households(id) ON DELETE CASCADE,
    UNIQUE(household_id, ingredient_name, unit)
);

-- Update indexes
CREATE INDEX IF NOT EXISTS idx_inventory_household_id ON inventory(household_id);
CREATE INDEX IF NOT EXISTS idx_users_household_id ON users(household_id);

-- Add trigger for households timestamp
CREATE TRIGGER IF NOT EXISTS update_households_timestamp 
    AFTER UPDATE ON households
    BEGIN
        UPDATE households SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;
