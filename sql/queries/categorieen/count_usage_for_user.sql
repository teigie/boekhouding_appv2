-- How many ledger rows (temp_afschrift + afschrift, both scoped to the
-- user's own accounts) currently carry this category. Used by
-- /categories to block deleting a category that's already in use rather
-- than orphaning historical data — Afschrift_cat_ID has no ON DELETE
-- CASCADE precisely so this has to be checked explicitly first.
-- Params: :cat_id, :user_id

SELECT
    (SELECT COUNT(*) FROM temp_afschrift t
       JOIN Rekening r ON r.ID = t.Rekening_ID
      WHERE t.Afschrift_cat_ID = :cat_id AND r.user_ID = :user_id)
  + (SELECT COUNT(*) FROM afschrift a
       JOIN Rekening r ON r.ID = a.Rekening_ID
      WHERE a.Afschrift_cat_ID = :cat_id AND r.user_ID = :user_id)
    AS usage_count;
