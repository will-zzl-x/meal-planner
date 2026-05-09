-- Slice 6: extend recipes with notes + tier, and recipe_ingredients with store.
-- (instructions column already exists from migration 005 but was unused.)
ALTER TABLE recipes ADD COLUMN notes TEXT;
ALTER TABLE recipes ADD COLUMN tier TEXT;  -- "S" | "A" | "B" | "C" | "D" | "E" | NULL

ALTER TABLE recipe_ingredients ADD COLUMN store TEXT;
