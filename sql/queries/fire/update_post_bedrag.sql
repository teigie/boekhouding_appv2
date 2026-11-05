-- Overwrites only the jaarbedrag of one pensioenplanner-post, leaving
-- every other editable field (groei_pct, start/stop_jaar, persoon,
-- actief, omschrijving) exactly as the user left it. Used by "Herbereken
-- bestaande posten" (app/routes/pensioenplanner.py::_herbereken_posten),
-- the counterpart to _sync_voorgestelde_posten that recomputes an
-- already-existing post's baseline instead of only adding missing ones.
-- Params: :id, :user_id, :jaarbedrag

UPDATE fire_posten SET
    jaarbedrag = :jaarbedrag,
    updated_at = datetime('now')
WHERE ID = :id AND user_ID = :user_id;
