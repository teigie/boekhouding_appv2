-- Deletes every temp_afschrift row for one account — the first step of
-- "Rekening verwijderen" on the profile page
-- (app/routes/accounts.py::delete_account), which removes an account and
-- its entire pending + migrated history in one transaction. Scoped
-- through Rekening.user_ID defensively, same style as
-- sql/migration/delete_from_temp_afschrift.sql — the caller should have
-- already verified ownership of :rekening_id via
-- sql/queries/rekeningen/find_by_id_for_user.sql.
-- Params: :rekening_id, :user_id

DELETE FROM temp_afschrift
WHERE Rekening_ID = :rekening_id
  AND Rekening_ID IN (SELECT ID FROM Rekening WHERE user_ID = :user_id);
