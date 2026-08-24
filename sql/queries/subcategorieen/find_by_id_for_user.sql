-- Look up one subcategory by ID, but only if it belongs to the given
-- user — so one user can't act on another user's subcategory through a
-- guessed ID. Mirrors sql/queries/categorieen/find_by_id_for_user.sql.
-- Includes cat_ID so the caller (delete_subcategory) knows which
-- category it belonged to. Params: :id, :user_id

SELECT ID, Name, cat_ID FROM afschrift_subcategorien WHERE ID = :id AND user_ID = :user_id;
