-- Add one column-condition to a rule (app/routes/categories.py::add_regel).
-- :kolom must be one of the 9 supported column names (enforced by
-- sql/schema.sql's CHECK constraint). This column's own keywords (added
-- right after, via add_regel_keyword.sql) always combine with AND.
--
-- Params: :regel_id, :kolom, :user_id

INSERT INTO afschrift_cat_regel_kolommen (regel_ID, kolom, user_ID)
VALUES (:regel_id, :kolom, :user_id);
