-- Deletes an account's temp_afschrift rows once migrated into afschrift
-- (insert_into_afschrift.sql), inside the same transaction. Draining the
-- full account backlog, never a partial subset, matches the same
-- all-or-nothing invariant categorize_batch.sql's
-- clear_temp_afschrift2.sql follows.
--
-- Params: :rekening_id, :user_id

DELETE FROM temp_afschrift
WHERE Rekening_ID = :rekening_id
  AND Rekening_ID IN (SELECT ID FROM Rekening WHERE user_ID = :user_id);
