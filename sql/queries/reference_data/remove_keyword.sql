-- Remove a keyword -> category link. Only affects future categorization runs —
-- rows already categorized in temp_afschrift/afschrift keep their
-- Afschrift_cat_ID and are not touched.
-- Params: :keyword

delete from afschrift_cat_keywords where keyword = :keyword;

-- Note: no "remove_category" query is provided by default. afschrift_cat_ID
-- is referenced by temp_afschrift/afschrift rows, so deleting a category
-- that's already in use would either violate the foreign key or orphan
-- historical data. If this is ever truly needed, decide first what should
-- happen to rows already carrying that category (reassign to "Overig"?).
