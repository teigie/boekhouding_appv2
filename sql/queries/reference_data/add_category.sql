-- Add a new spending category, owned by a user. description is always
-- optional — :description may be NULL. :type is the Inkomsten/Uitgaven
-- super-classification (see sql/schema.sql) — NOT NULL on the table, so
-- the caller (app/routes/categories.py) always resolves a concrete
-- value before this runs (falling back to 'Uitgaven' when the current
-- bare-bones "Nieuwe categorie" form doesn't collect one yet), never
-- NULL itself.
-- Params: :name, :description, :type, :user_id

insert into afschrift_categorien (Name, description, Type, user_ID) values (:name, :description, :type, :user_id);
