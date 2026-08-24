-- Sets (or clears, if :subcat_id is NULL) an existing rule's assigned
-- subcategory — used by the rule-edit page (/categories/regels/{id}/edit)
-- to update just this one field, separately from the wholesale
-- column/keyword replace that page already does (see
-- remove_regel_kolommen_for_regel.sql). Scoped to the given user so one
-- user can't repoint another user's rule through a guessed ID. Also
-- requires :subcat_id to belong to the SAME category as the rule itself
-- — subcategories are scoped to one category (see sql/schema.sql), so a
-- guessed/stale subcat_id from a different one of the user's categories
-- must never attach. If either check fails, the UPDATE simply matches
-- zero rows rather than erroring (same pattern as
-- sql/queries/temp_afschrift/set_category.sql).
-- Params: :regel_id, :subcat_id, :user_id

UPDATE afschrift_cat_regels
SET subcat_ID = :subcat_id
WHERE ID = :regel_id
  AND user_ID = :user_id
  AND (
    :subcat_id IS NULL
    OR :subcat_id IN (
        SELECT sc.ID FROM afschrift_subcategorien sc
        WHERE sc.cat_ID = (SELECT r.cat_ID FROM afschrift_cat_regels r WHERE r.ID = :regel_id)
    )
  );
