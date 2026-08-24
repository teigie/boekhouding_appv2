-- One category's own subcategories, for the /categories rule form's
-- dropdown and the profile page's per-category subcategory management
-- block — subcategories are scoped to exactly one category (see
-- sql/schema.sql), so this is the query to use anywhere a category is
-- already known and only ITS subcategories should be offered.
-- Params: :cat_id, :user_id

SELECT ID, Name FROM afschrift_subcategorien WHERE cat_ID = :cat_id AND user_ID = :user_id ORDER BY Name;
