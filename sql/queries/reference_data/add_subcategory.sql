-- Add a new subcategory under a category, owned by a user. Subcategories
-- are scoped to exactly one category (see sql/schema.sql) — :cat_id is
-- the category it belongs to. description is always optional — may be
-- NULL.
-- Params: :name, :description, :cat_id, :user_id

insert into afschrift_subcategorien (Name, description, cat_ID, user_ID) values (:name, :description, :cat_id, :user_id);
