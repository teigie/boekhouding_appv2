-- Called on every successful login.
-- Params: :user_id

UPDATE Users SET last_logged_in = datetime('now') WHERE ID = :user_id;
