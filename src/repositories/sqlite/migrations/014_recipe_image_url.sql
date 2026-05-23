-- Slice B2: optional image URL per recipe. The user pastes a link (from a
-- blog, IG screenshot host, etc.); we show the image at the top of the
-- recipe card. Stored as a URL — we don't host images.
ALTER TABLE recipes ADD COLUMN image_url TEXT;
