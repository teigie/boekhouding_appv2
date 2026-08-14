-- Link a new keyword to a category, so future categorization runs auto-assign
-- that category to any transaction whose Naam/Mededeling contains it.
-- Params: :keyword, :cat_id

insert into afschrift_cat_keywords (keyword, cat_ID) values (:keyword, :cat_id);
