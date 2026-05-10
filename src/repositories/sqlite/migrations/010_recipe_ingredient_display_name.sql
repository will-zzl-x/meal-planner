-- Task 2 (overnight): preserve the user-typed ingredient name on each
-- recipe row, separately from the catalog row's canonical name.
--
-- Without this, the recipe repo's read path always pulls the ingredient's
-- name from the joined catalog row — so a backfilled recipe would display
-- "Chicken Breast" instead of the seed-author-typed "Skinless chicken
-- thighs (~4 thighs)". The catalog link is still made via ingredient_id;
-- this column just gives us a place to remember the user's phrasing.
ALTER TABLE recipe_ingredients ADD COLUMN display_name TEXT;
