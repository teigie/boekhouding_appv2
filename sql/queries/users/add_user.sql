-- Create a new user. No password field — see docs/ARCHITECTURE.md for why.
-- Params: :name

INSERT INTO Users (Name, creation_date) VALUES (:name, datetime('now'));
