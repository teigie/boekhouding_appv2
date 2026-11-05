-- Sets whether one Rekening counts toward the pensioenplanner baseline.
-- Scoped on (user_ID, Rekening_ID) together, matching
-- fire_rekening_selectie's primary key.
-- Params: :user_id, :rekening_id, :actief

UPDATE fire_rekening_selectie SET actief = :actief
WHERE user_ID = :user_id AND Rekening_ID = :rekening_id;
