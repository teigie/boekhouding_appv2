-- One rule's current column-conditions and their keywords, to pre-fill
-- the rule-edit page (/categories/regels/{regel_id}/edit) — the caller
-- (app/routes/categories.py) groups this flat result by kolom.
--
-- Params: :regel_id, :user_id

SELECT gk.kolom, gk.combine_mode, k.keyword
FROM afschrift_cat_regel_kolommen gk
JOIN afschrift_cat_regel_keywords k ON k.regel_kolom_ID = gk.ID
WHERE gk.regel_ID = :regel_id
  AND gk.user_ID = :user_id
ORDER BY gk.ID, k.ID;
