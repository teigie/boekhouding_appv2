-- The pensioenplanner's single settings row for one user, or no row at
-- all if they've never opened the instellingen page (see
-- app/routes/pensioenplanner.py, which seeds a default row + auto-fills
-- posten the first time this comes back empty).
-- Params: :user_id

SELECT * FROM fire_instellingen WHERE user_ID = :user_id;
