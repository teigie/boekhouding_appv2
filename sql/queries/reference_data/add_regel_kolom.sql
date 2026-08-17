-- Add one column-condition to a rule (app/routes/categories.py::add_regel).
-- :kolom must be one of the 9 supported column names (enforced by
-- sql/schema.sql's CHECK constraint); :combine_mode is 'AND' or 'OR',
-- governing how this column's own keywords (added right after, via
-- add_regel_keyword.sql) combine with each other.
--
-- Params: :regel_id, :kolom, :combine_mode, :user_id

INSERT INTO afschrift_cat_regel_kolommen (regel_ID, kolom, combine_mode, user_ID)
VALUES (:regel_id, :kolom, :combine_mode, :user_id);
