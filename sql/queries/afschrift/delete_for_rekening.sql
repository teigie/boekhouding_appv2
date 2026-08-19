-- Deletes every afschrift row (permanent ledger history) for one
-- account — the second step of "Rekening verwijderen" on the profile page
-- (app/routes/accounts.py::delete_account), run in the same transaction
-- as sql/queries/temp_afschrift/delete_for_rekening.sql right before the
-- Rekening row itself is removed. This is the one place in the app that
-- deletes from afschrift at all — normally append-only (see
-- docs/ARCHITECTURE.md) once a row is migrated in, but removing the
-- owning account takes its whole ledger with it, with no partial option.
-- Scoped through Rekening.user_ID defensively, same style as
-- sql/queries/temp_afschrift/delete_for_rekening.sql.
-- Params: :rekening_id, :user_id

DELETE FROM afschrift
WHERE Rekening_ID = :rekening_id
  AND Rekening_ID IN (SELECT ID FROM Rekening WHERE user_ID = :user_id);
