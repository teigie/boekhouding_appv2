-- Link an account (IBAN, stored in the "name" column) to a user. Used
-- both at signup (a new user must provide their first Rekening in the
-- same step) and later on the Accounts screen (linking an additional
-- Rekening to an existing user).
--
-- name is UNIQUE across all users — an account number can only ever
-- belong to one user system-wide, so this fails with an IntegrityError
-- if it's already registered (to anyone).
--
-- Params: :name (the IBAN/account-number value), :user_id

INSERT INTO Rekening (name, creation_date, user_ID) VALUES (:name, datetime('now'), :user_id);
