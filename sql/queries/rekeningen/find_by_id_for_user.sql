-- Resolve a Rekening.ID, scoped to a given user — used wherever a route
-- takes an account ID from the URL and needs to confirm it's actually the
-- logged-in user's before acting on it (e.g. /review's per-table save).
-- Params: :id, :user_id

SELECT ID, name FROM Rekening WHERE ID = :id AND user_ID = :user_id;
