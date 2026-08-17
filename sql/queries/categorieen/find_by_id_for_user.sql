-- Look up one category by ID, but only if it belongs to the given user —
-- so one user can't act on another user's category through a guessed ID.
-- Mirrors sql/queries/rekeningen/find_by_id_for_user.sql.
-- Params: :id, :user_id

SELECT ID, Name FROM afschrift_categorien WHERE ID = :id AND user_ID = :user_id;
