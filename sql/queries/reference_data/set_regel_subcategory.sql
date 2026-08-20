-- Sets (or clears, if :subcat_id is NULL) an existing rule's assigned
-- subcategory — used by the rule-edit page (/categories/regels/{id}/edit)
-- to update just this one field, separately from the wholesale
-- column/keyword replace that page already does (see
-- remove_regel_kolommen_for_regel.sql). Scoped to the given user so one
-- user can't repoint another user's rule through a guessed ID.
-- Params: :regel_id, :subcat_id, :user_id

UPDATE afschrift_cat_regels
SET subcat_ID = :subcat_id
WHERE ID = :regel_id
  AND user_ID = :user_id;
