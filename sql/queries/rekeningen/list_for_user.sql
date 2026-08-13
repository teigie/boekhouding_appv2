-- All accounts linked to a user, for the Accounts screen.
-- Params: :user_id

SELECT ID, name, creation_date FROM Rekening WHERE user_ID = :user_id ORDER BY creation_date;
