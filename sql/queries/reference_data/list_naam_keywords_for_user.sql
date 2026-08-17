-- All of a user's "simple" (Naam) keywords, for /categories. Grouped by
-- category in Python after fetching.
-- Params: :user_id

SELECT ID, keyword, cat_ID FROM afschrift_cat_keywords WHERE user_ID = :user_id ORDER BY cat_ID, keyword COLLATE NOCASE;
