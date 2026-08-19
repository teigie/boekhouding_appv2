-- How many ledger rows (temp_afschrift + afschrift) currently belong to
-- this account — shown in the "Rekening verwijderen" confirmation warning
-- on the profile page so the user knows exactly how much history that
-- takes with it before confirming. Same scoped-subquery shape as
-- sql/queries/categorieen/count_usage_for_user.sql.
-- Params: :rekening_id, :user_id

SELECT
    (SELECT COUNT(*) FROM temp_afschrift t
       JOIN Rekening r ON r.ID = t.Rekening_ID
      WHERE t.Rekening_ID = :rekening_id AND r.user_ID = :user_id)
  + (SELECT COUNT(*) FROM afschrift a
       JOIN Rekening r ON r.ID = a.Rekening_ID
      WHERE a.Rekening_ID = :rekening_id AND r.user_ID = :user_id)
    AS row_count;
