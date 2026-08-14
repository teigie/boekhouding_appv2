-- Deletes an account's entire temp_afschrift2 backlog once its rows have
-- been categorized into temp_afschrift (categorize_batch.sql), inside the
-- same transaction. Draining the full backlog, never a partial subset, is
-- required by the balance-chain ordering invariant — see
-- docs/ARCHITECTURE.md.
--
-- Params:
--   :rekening_text — raw account text as it appears in temp_afschrift2.Rekening

DELETE FROM temp_afschrift2
WHERE Rekening = :rekening_text;
