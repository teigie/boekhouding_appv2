-- Every Rekening linked to this user, with whether it currently counts
-- toward the pensioenplanner baseline (fire_rekening_selectie.actief) —
-- for the instellingen page's "Rekeningen" checkbox list. Assumes
-- sync_rekening_selectie.sql has already been run this request, so every
-- Rekening has a row.
-- Params: :user_id

SELECT r.ID AS rekening_id, r.name AS rekening_naam, frs.actief
FROM Rekening r
JOIN fire_rekening_selectie frs ON frs.Rekening_ID = r.ID AND frs.user_ID = r.user_ID
WHERE r.user_ID = :user_id
ORDER BY r.name;
