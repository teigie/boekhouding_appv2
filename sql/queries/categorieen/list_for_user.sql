-- A user's spending categories, for the dashboard, /review's dropdown,
-- and /categories.
-- Params: :user_id

SELECT ID, Name FROM afschrift_categorien WHERE user_ID = :user_id ORDER BY Name;
