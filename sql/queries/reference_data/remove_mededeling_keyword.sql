-- Remove a "difficult" keyword -> category link, by ID + ownership check.
-- Same semantics as remove_naam_keyword.sql, against the mededeling table.
-- Params: :id, :user_id

delete from afschrift_cat_mededeling_keywords where ID = :id and user_ID = :user_id;
