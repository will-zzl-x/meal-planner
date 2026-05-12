-- Drop the recipe tier column. The S/A/B/C rating system was removed end-to-end
-- in this change (domain model, repository, views, tests, seed recipes). Dropping
-- the column too keeps the schema in sync with the code; the data it held was
-- only the seed recipes' presets, never user-curated, so nothing of value lost.
-- SQLite doesn't accept "IF EXISTS" on DROP COLUMN, but migration 008 always
-- adds this column, so by the time 012 runs it's guaranteed to exist on every
-- DB the migration runner can reach.
ALTER TABLE recipes DROP COLUMN tier;
