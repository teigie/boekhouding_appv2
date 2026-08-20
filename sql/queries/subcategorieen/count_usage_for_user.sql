-- How many ledger rows (temp_afschrift + afschrift, both scoped to the
-- user's own accounts) currently carry this subcategory. Used to block
-- deleting a subcategory that's already in use rather than orphaning
-- historical data — Afschrift_subcat_ID has no ON DELETE CASCADE/SET NULL
-- precisely so this has to be checked explicitly first. Mirrors
-- sql/queries/categorieen/count_usage_for_user.sql — rules that assign
-- this subcategory are NOT counted here (afschrift_cat_regels.subcat_ID
-- is ON DELETE SET NULL, so those simply lose the subcategory, the rule
-- itself keeps working for its category).
-- Params: :subcat_id, :user_id

SELECT
    (SELECT COUNT(*) FROM temp_afschrift t
       JOIN Rekening r ON r.ID = t.Rekening_ID
      WHERE t.Afschrift_subcat_ID = :subcat_id AND r.user_ID = :user_id)
  + (SELECT COUNT(*) FROM afschrift a
       JOIN Rekening r ON r.ID = a.Rekening_ID
      WHERE a.Afschrift_subcat_ID = :subcat_id AND r.user_ID = :user_id)
    AS usage_count;
