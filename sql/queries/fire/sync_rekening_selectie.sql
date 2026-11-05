-- Adds a fire_rekening_selectie row (actief=1, i.e. included) for every
-- Rekening of this user that doesn't have one yet — run on every visit to
-- the instellingen page (app/routes/pensioenplanner.py::instellingen_page),
-- not just once, since a Rekening can be linked at any time (see
-- app/routes/accounts.py). Never touches a row that already exists, so a
-- previously deselected account stays deselected.
-- Params: :user_id

INSERT INTO fire_rekening_selectie (user_ID, Rekening_ID, actief)
SELECT r.user_ID, r.ID, 1
FROM Rekening r
WHERE r.user_ID = :user_id
  AND NOT EXISTS (
      SELECT 1 FROM fire_rekening_selectie frs
      WHERE frs.user_ID = r.user_ID AND frs.Rekening_ID = r.ID
  );
