-- Add a new subcategory under a category, owned by a user. Subcategories
-- are scoped to exactly one category (see sql/schema.sql) — :cat_id is
-- the category it belongs to.
-- Params: :name, :cat_id, :user_id

insert into afschrift_subcategorien (Name, cat_ID, user_ID) values (:name, :cat_id, :user_id);
