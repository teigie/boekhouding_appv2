-- Earliest/latest Datum across a user's permanent-ledger rows, used to
-- build the dashboard's "Alles" (all time) month-range preset from the
-- user's actual data instead of an arbitrary epoch placeholder — so the
-- <input type="month"> preset value is always a real, sensible month.
-- NULL/NULL (no rows yet) is handled by the caller, which falls back to
-- the current month.
--
-- Params: :user_id

SELECT MIN(a.Datum) AS min_datum, MAX(a.Datum) AS max_datum
FROM afschrift a
JOIN Rekening r ON r.ID = a.Rekening_ID
WHERE r.user_ID = :user_id;
