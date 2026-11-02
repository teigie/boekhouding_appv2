-- All tracked people for one user's pensioenplanner (see
-- sql/schema.sql::fire_personen).
-- Params: :user_id

SELECT ID, naam, geboortejaar FROM fire_personen WHERE user_ID = :user_id ORDER BY naam;
