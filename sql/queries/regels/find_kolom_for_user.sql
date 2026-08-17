-- Ownership check before adding another keyword to an existing rule's
-- existing column-condition (app/routes/categories.py) — confirms
-- :kolom_id both belongs to :regel_id and is the given user's own.
--
-- Params: :kolom_id, :regel_id, :user_id

SELECT ID, kolom, combine_mode
FROM afschrift_cat_regel_kolommen
WHERE ID = :kolom_id
  AND regel_ID = :regel_id
  AND user_ID = :user_id;
