-- Freezes the projection's predicted totals for one year, at save time —
-- rebased on the latest known werkelijke/lopende cijfers, see
-- app/routes/pensioenplanner.py::_update_prognose_snapshot. Only ever
-- called for a year that isn't "werkelijk" yet; a year that has since
-- become werkelijk is simply never passed in again, so its last row here
-- stays frozen.
-- Params: :user_id, :jaar, :voorspeld_inkomsten, :voorspeld_uitgaven,
--         :voorspeld_netto, :voorspeld_totaal

INSERT INTO fire_prognose_snapshot (
    user_ID, jaar, voorspeld_inkomsten, voorspeld_uitgaven, voorspeld_netto, voorspeld_totaal,
    updated_at
) VALUES (
    :user_id, :jaar, :voorspeld_inkomsten, :voorspeld_uitgaven, :voorspeld_netto, :voorspeld_totaal,
    datetime('now')
)
ON CONFLICT(user_ID, jaar) DO UPDATE SET
    voorspeld_inkomsten = excluded.voorspeld_inkomsten,
    voorspeld_uitgaven = excluded.voorspeld_uitgaven,
    voorspeld_netto = excluded.voorspeld_netto,
    voorspeld_totaal = excluded.voorspeld_totaal,
    updated_at = excluded.updated_at;
