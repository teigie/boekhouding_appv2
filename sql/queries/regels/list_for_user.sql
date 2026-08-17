-- Every categorization rule belonging to the given user, with its
-- column-conditions and their keywords, for display on the profile page.
-- One row per keyword; the caller (app/user_page.py) groups this flat
-- result into cat_ID -> regel -> kolom -> keywords nesting.
--
-- A rule with zero column-conditions (shouldn't normally exist — see
-- sql/schema.sql's comment on afschrift_cat_regel_kolommen) simply
-- doesn't appear via this INNER JOIN, which is fine: it wouldn't match
-- anything (see match_custom_rules.sql) and there's nothing meaningful
-- to render for it anyway.
--
-- Params: :user_id

SELECT
    r.ID AS regel_ID,
    r.cat_ID,
    gk.ID AS kolom_ID,
    gk.kolom,
    gk.combine_mode,
    k.ID AS keyword_ID,
    k.keyword
FROM afschrift_cat_regels r
JOIN afschrift_cat_regel_kolommen gk ON gk.regel_ID = r.ID
JOIN afschrift_cat_regel_keywords k ON k.regel_kolom_ID = gk.ID
WHERE r.user_ID = :user_id
ORDER BY r.cat_ID, r.ID, gk.ID, k.ID;
