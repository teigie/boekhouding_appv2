-- Add one keyword/value to a rule's column-condition. Already normalized
-- for its column by app/categorization_rules.py::normalize_keyword
-- before this runs (e.g. a Dutch-formatted amount already parsed into
-- its canonical numeric string, Af_bij already restricted to 'Af'/'Bij').
--
-- Params: :regel_kolom_id, :keyword, :user_id

INSERT INTO afschrift_cat_regel_keywords (regel_kolom_ID, keyword, user_ID)
VALUES (:regel_kolom_id, :keyword, :user_id);
