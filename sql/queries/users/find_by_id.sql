-- Look up a user by ID (used when confirming a /login selection).
-- Includes last_logged_in so the caller can capture it as "previous
-- login" BEFORE touch_last_logged_in.sql overwrites it with now().
-- Params: :user_id

SELECT ID, Name, last_logged_in FROM Users WHERE ID = :user_id;
