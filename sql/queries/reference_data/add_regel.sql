-- Create a new (initially condition-less) categorization rule under a
-- category. The caller adds its column-conditions (add_regel_kolom.sql)
-- and their keywords (add_regel_keyword.sql) right after, in the same
-- transaction — see app/routes/categories.py::add_regel.
--
-- Params: :cat_id, :user_id

INSERT INTO afschrift_cat_regels (cat_ID, user_ID) VALUES (:cat_id, :user_id);
