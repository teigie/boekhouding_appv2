-- Delete a single keyword from a rule's column-condition, scoped to its
-- owning user. Doesn't touch the now-possibly-empty column-condition row
-- itself — see remove_empty_regel_kolommen.sql, run right after in the
-- same transaction (app/routes/categories.py::remove_regel_keyword).
--
-- Params: :id, :user_id

DELETE FROM afschrift_cat_regel_keywords WHERE ID = :id AND user_ID = :user_id;
