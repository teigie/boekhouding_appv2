-- Link a new "simple" keyword to a category the user owns, so future
-- categorization runs auto-assign that category to any transaction whose
-- Naam contains it. Caller must have already verified the category
-- belongs to :user_id (see categorieen/find_by_id_for_user.sql).
-- Params: :keyword, :cat_id, :user_id

insert into afschrift_cat_keywords (keyword, cat_ID, user_ID) values (:keyword, :cat_id, :user_id);
