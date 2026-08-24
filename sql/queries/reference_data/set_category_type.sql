-- Sets an existing category's Type (Inkomsten/Uitgaven
-- super-classification, see sql/schema.sql) — NOT NULL on the table, so
-- :type must already be a validated 'Inkomsten'/'Uitgaven' by the time
-- this runs (app/routes/categories.py rejects anything else before
-- getting here, rather than silently defaulting or clearing — unlike
-- description, this field always needs a deliberate, correct value).
-- Scoped to the given user so one user can't repoint another user's
-- category through a guessed ID.
-- Params: :cat_id, :type, :user_id

UPDATE afschrift_categorien
SET Type = :type
WHERE ID = :cat_id
  AND user_ID = :user_id;
