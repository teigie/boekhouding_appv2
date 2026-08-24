-- Sets (or clears, if :description is NULL/empty) an existing
-- category's description — a free-form, always-optional note, never
-- read by matching/filtering logic. Scoped to the given user so one
-- user can't repoint another user's category through a guessed ID.
-- Params: :cat_id, :description, :user_id

UPDATE afschrift_categorien
SET description = :description
WHERE ID = :cat_id
  AND user_ID = :user_id;
