-- A user's subcategories, for the /categories rule form's dropdown,
-- /review's dropdown, and the dashboard's filter — one shared list, not
-- scoped to any single category (see sql/schema.sql).
-- Params: :user_id

SELECT ID, Name FROM afschrift_subcategorien WHERE user_ID = :user_id ORDER BY Name;
