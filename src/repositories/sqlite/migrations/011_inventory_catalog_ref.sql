-- V2-1: pantry items can reference the same catalog rows recipe
-- ingredients use, so coverage matching can be exact instead of name-
-- based. Existing inventory rows stay with NULL catalog_ingredient_id;
-- code paths fall back to legacy name+unit matching for those.
--
-- No FK constraint on purpose — catalog rows can be deleted, and
-- orphaning a pantry row shouldn't crash anything.
ALTER TABLE inventory ADD COLUMN catalog_ingredient_id TEXT;

CREATE INDEX IF NOT EXISTS idx_inventory_catalog_ref
    ON inventory(household_id, catalog_ingredient_id);
