-- Look up one subcategory by ID, but only if it belongs to the given
-- user — so one user can't act on another user's subcategory through a
-- guessed ID. Mirrors sql/queries/categorieen/find_by_id_for_user.sql.
-- Params: :id, :user_id

SELECT ID, Name FROM afschrift_subcategorien WHERE ID = :id AND user_ID = :user_id;
