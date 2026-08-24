-- Look up one of a category's own subcategories by name,
-- case-insensitively — reuses an existing subcategory instead of
-- creating a near-duplicate from a typo'd name that already exists under
-- the same category. Used by the "nieuwe subcategorie…" inline-create
-- option on /categories' rule form and on /review, mirroring
-- sql/queries/categorieen/find_by_name.sql. Scoped to :cat_id, not just
-- :user_id — the same name is allowed to exist under a different
-- category (see sql/schema.sql's unique (cat_ID, Name)).
-- Params: :cat_id, :user_id, :name

SELECT ID, Name FROM afschrift_subcategorien WHERE cat_ID = :cat_id AND user_ID = :user_id AND Name = :name COLLATE NOCASE;
