-- Remove a "simple" keyword -> category link, by ID (keyword text is only
-- unique per-user now, not globally, so ID + ownership check is used
-- instead of matching on text). Only affects future categorization runs —
-- rows already categorized in temp_afschrift/afschrift keep their
-- Afschrift_cat_ID and are not touched.
-- Params: :id, :user_id

delete from afschrift_cat_keywords where ID = :id and user_ID = :user_id;
