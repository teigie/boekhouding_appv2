-- Wipes a rule's ENTIRE current set of column-conditions (cascades their
-- keywords, ON DELETE CASCADE), as the first half of the rule-edit
-- page's "replace" semantics — the caller re-inserts whatever columns
-- were actually submitted right after, in the same transaction (see
-- app/routes/categories.py::save_regel). Never leaves the rule
-- column-less on its own: the caller validates there's at least one
-- non-empty column in the submission BEFORE running this delete.
--
-- Params: :regel_id, :user_id

DELETE FROM afschrift_cat_regel_kolommen
WHERE regel_ID = :regel_id
  AND user_ID = :user_id;
