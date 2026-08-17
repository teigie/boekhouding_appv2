-- Ownership check before showing/saving the rule-edit page
-- (/categories/regels/{regel_id}/edit) — confirms :id belongs to
-- :user_id, and resolves the owning category's name for display.
--
-- Params: :id, :user_id

SELECT r.ID, r.cat_ID, c.Name AS category_name
FROM afschrift_cat_regels r
JOIN afschrift_categorien c ON c.ID = r.cat_ID
WHERE r.ID = :id
  AND r.user_ID = :user_id;
