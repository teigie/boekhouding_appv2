-- Sets (or clears, if :description is NULL/empty) an existing
-- subcategory's description — a free-form, always-optional note, never
-- read by matching/filtering logic. Scoped to the given user so one
-- user can't repoint another user's subcategory through a guessed ID.
-- Params: :subcat_id, :description, :user_id

UPDATE afschrift_subcategorien
SET description = :description
WHERE ID = :subcat_id
  AND user_ID = :user_id;
