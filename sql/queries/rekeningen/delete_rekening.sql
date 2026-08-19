-- Removes an account itself. Must run after its temp_afschrift/afschrift
-- rows have already been cleared in the same transaction (see
-- app/routes/accounts.py::delete_account and
-- sql/queries/temp_afschrift/delete_for_rekening.sql,
-- sql/queries/afschrift/delete_for_rekening.sql) — deleting a Rekening
-- still referenced by either table would otherwise fail on the foreign
-- key, since neither has ON DELETE CASCADE.
-- Params: :id, :user_id

DELETE FROM Rekening WHERE ID = :id AND user_ID = :user_id;
