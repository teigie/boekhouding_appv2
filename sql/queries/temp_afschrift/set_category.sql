-- Manually set (or override) a temp_afschrift row's category and (always
-- optional) subcategory, from the /review page's per-row dropdowns — run
-- once per row when a table's single save button is submitted. Setting a
-- category here always marks the row resolved (processed = 1) — a human
-- just made the call, whether the row was previously unresolved,
-- ambiguous, or already resolved to something else. :subcat_id may be
-- NULL — that's an explicit, active "no subcategory" choice, not "leave
-- whatever was there", so it's always written, never skipped.
--
-- Scoped to the given user via a Rekening ownership check, so one user
-- can't repoint another user's row through a guessed ID. Also requires
-- :cat_id itself to belong to :user_id — categories are per-user now, so
-- without this a guessed/stale cat_id could point at another user's
-- category. Same check for :subcat_id, except NULL is always allowed
-- (skips the ownership check entirely) since "no subcategory" needs no
-- ownership. If :cat_id/:subcat_id isn't the user's, the UPDATE simply
-- matches zero rows rather than erroring.
--
-- Params: :id, :cat_id, :subcat_id, :user_id

UPDATE temp_afschrift
SET Afschrift_cat_ID = :cat_id, Afschrift_subcat_ID = :subcat_id, processed = 1
WHERE ID = :id
  AND Rekening_ID IN (SELECT ID FROM Rekening WHERE user_ID = :user_id)
  AND :cat_id IN (SELECT ID FROM afschrift_categorien WHERE user_ID = :user_id)
  AND (:subcat_id IS NULL OR :subcat_id IN (SELECT ID FROM afschrift_subcategorien WHERE user_ID = :user_id));
