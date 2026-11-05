-- Pensioenplanner-specific counterpart to
-- sql/queries/afschrift/date_bounds_for_user.sql (which the dashboard's
-- "Alles" month-range preset uses, unfiltered by Rekening — kept separate
-- and untouched so this feature never changes that preset's behavior).
-- This version only looks at Rekeningen the user has included via
-- fire_rekening_selectie (see sync_rekening_selectie.sql) — used by
-- app/routes/pensioenplanner.py::_baseline_venster to anchor the
-- auto-suggestion window to the last real afschrift date among the
-- accounts that actually feed the baseline.
-- Params: :user_id

SELECT MIN(a.Datum) AS min_datum, MAX(a.Datum) AS max_datum
FROM afschrift a
JOIN Rekening r ON r.ID = a.Rekening_ID
JOIN fire_rekening_selectie frs ON frs.Rekening_ID = r.ID AND frs.user_ID = r.user_ID
WHERE r.user_ID = :user_id AND frs.actief = 1;
