-- ALL of a user's subcategories across ALL of their categories, each
-- tagged with its own cat_ID/cat_name — for the two places that need to
-- offer/filter across categories at once rather than within one already-
-- known category (see list_for_category.sql for that narrower case):
-- /review's per-row dropdown (filtered client-side to whichever category
-- that row currently has, since either can be changed inline — see
-- app/static/js/review.js) and the dashboard's filter (grouped by
-- category in the label so a flat checkbox list stays readable, see
-- app/templates/index.html).
-- Params: :user_id

SELECT sc.ID, sc.Name, sc.description, sc.cat_ID, c.Name AS cat_name
FROM afschrift_subcategorien sc
JOIN afschrift_categorien c ON c.ID = sc.cat_ID
WHERE sc.user_ID = :user_id
ORDER BY c.Name, sc.Name;
