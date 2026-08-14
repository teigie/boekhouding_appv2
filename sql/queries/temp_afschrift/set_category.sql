-- Manually set (or override) a temp_afschrift row's category, from the
-- /review page's per-row dropdown — run once per row when a table's single
-- save button is submitted. Setting a category here always marks the row
-- resolved (processed = 1) — a human just made the call, whether the row
-- was previously unresolved, ambiguous, or already resolved to something
-- else.
--
-- Scoped to the given user via a Rekening ownership check, so one user
-- can't repoint another user's row through a guessed ID.
--
-- Params: :id, :cat_id, :user_id

UPDATE temp_afschrift
SET Afschrift_cat_ID = :cat_id, processed = 1
WHERE ID = :id
  AND Rekening_ID IN (SELECT ID FROM Rekening WHERE user_ID = :user_id);
