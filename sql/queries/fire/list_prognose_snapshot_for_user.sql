-- All frozen per-year predictions for one user — used by
-- app/routes/pensioenplanner.py::pensioenplanner_page/export_csv to show
-- how far a now-werkelijk or lopend year's prediction was off.
-- Params: :user_id

SELECT jaar, voorspeld_inkomsten, voorspeld_uitgaven, voorspeld_netto, voorspeld_totaal
FROM fire_prognose_snapshot
WHERE user_ID = :user_id;
