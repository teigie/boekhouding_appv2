-- Verifies an account's full sequence — confirmed ledger + pending
-- categorization + newly-uploaded rows — never has a date that comes
-- before the row right before it. Equal dates are fine (several
-- transactions on the same day); only a step *backwards* is a
-- violation. Same ordering convention as check_balance_chain.sql
-- ("table, then that table's own ID" reconstructs the correct global
-- order — see that file's comment for why this works without the three
-- ID columns needing to relate to each other), just checking Datum's
-- flow instead of the balance chain — an independent structural check,
-- catching a scrambled/out-of-order file even in the rare case its
-- balance still happens to chain correctly across the reordered rows.
--
-- Returns the offending rows; an empty result means every row's date is
-- the same as or later than the one before it, and the just-inserted
-- batch is safe to commit alongside the other post-insert checks.
--
-- Date formats differ across tables (temp_afschrift2.Datum is the raw
-- "YYYYMMDD" from the bank file; temp_afschrift/afschrift.Datum is
-- "YYYY-MM-DD" once categorization has run) — temp_afschrift2's Datum is
-- normalized to "YYYY-MM-DD" here first, same as check_dedup.sql, so
-- plain string comparison sorts chronologically either way.
--
-- Run this AFTER inserting the new batch into temp_afschrift2, inside
-- the same transaction as check_balance_chain.sql/check_batch_totals.sql/
-- check_dedup.sql — roll back if this returns any rows.
--
-- Params:
--   :rekening_text — raw account text as it appears in temp_afschrift2.Rekening
--   :rekening_id   — resolved Rekening.ID, or NULL if the account isn't linked yet

WITH sequence AS (
    SELECT ID, Datum, Naam, 0 AS table_order
    FROM afschrift
    WHERE Rekening_ID = :rekening_id

    UNION ALL

    SELECT ID, Datum, Naam, 1 AS table_order
    FROM temp_afschrift
    WHERE Rekening_ID = :rekening_id

    UNION ALL

    SELECT
        ID,
        substr(Datum, 1, 4) || '-' || substr(Datum, 5, 2) || '-' || substr(Datum, 7, 2) AS Datum,
        Naam,
        2 AS table_order
    FROM temp_afschrift2
    WHERE Rekening = :rekening_text
),
checked AS (
    SELECT
        *,
        LAG(Datum) OVER (ORDER BY table_order, ID) AS prev_datum
    FROM sequence
)
SELECT *
FROM checked
WHERE prev_datum IS NOT NULL
  AND Datum < prev_datum;
