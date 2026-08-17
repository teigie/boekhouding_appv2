-- Link a new "difficult" keyword/phrase to a category the user owns, so
-- future categorization runs auto-assign that category to any
-- transaction whose Mededeling contains it. Caller must have already
-- verified the category belongs to :user_id (see
-- categorieen/find_by_id_for_user.sql).
--
-- :naam_keyword is optional (pass NULL/None to omit) — when given, this
-- keyword only matches transactions whose Naam ALSO contains it (see
-- sql/schema.sql's comment on afschrift_cat_mededeling_keywords for why).
--
-- Params: :keyword, :naam_keyword, :cat_id, :user_id

insert into afschrift_cat_mededeling_keywords (keyword, naam_keyword, cat_ID, user_ID)
values (:keyword, :naam_keyword, :cat_id, :user_id);
