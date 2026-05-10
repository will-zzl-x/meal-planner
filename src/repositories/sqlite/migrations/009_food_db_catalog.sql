-- Slice 8a: extend the `ingredients` catalog so it can hold what real
-- nutrition databases (USDA, Open Food Facts) return.
--
-- Per-serving columns are added alongside the existing per-100g columns;
-- per-100g stays for backwards compatibility with anything still using it.
-- `source` + `external_id` lets us recognize a previously-cached item from
-- the same database and reuse its row instead of inserting duplicates.
ALTER TABLE ingredients ADD COLUMN brand TEXT;
ALTER TABLE ingredients ADD COLUMN serving_label TEXT;          -- "1 cup", "100g", "1 large egg"
ALTER TABLE ingredients ADD COLUMN calories_per_serving INTEGER;
ALTER TABLE ingredients ADD COLUMN protein_per_serving DECIMAL(6,2);
ALTER TABLE ingredients ADD COLUMN carbs_per_serving DECIMAL(6,2);
ALTER TABLE ingredients ADD COLUMN fat_per_serving DECIMAL(6,2);
ALTER TABLE ingredients ADD COLUMN source TEXT;                 -- "usda" | "openfoodfacts" | "manual"
ALTER TABLE ingredients ADD COLUMN external_id TEXT;

CREATE INDEX IF NOT EXISTS idx_ingredients_source_external_id
    ON ingredients(source, external_id);
