-- Resolve an account's raw text (as it appears in an uploaded file, or
-- anywhere else) to its Rekening.ID + owning user, if it's registered.
-- Params: :name

SELECT ID, user_ID FROM Rekening WHERE name = :name;
