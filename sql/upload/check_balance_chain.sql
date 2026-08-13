-- Verifies an account's full sequence — confirmed ledger + pending
-- enrichment + newly-uploaded rows — has no broken balance link anywhere.
-- Returns the offending rows; an empty result means the chain is intact
-- and the just-inserted batch is safe to commit.
--
-- Run this AFTER inserting the new batch into temp_afschrift2, inside the
-- same transaction — roll back if this returns any rows.
--
-- Ordering: afschrift.ID is the permanent, globally meaningful sequence
-- for an account (it's the append-only ledger — once a row lands there it
-- never moves). temp_afschrift/temp_afschrift2's own IDs only matter
-- *within* that table — to order rows inside one batch, and to order
-- multiple batches that have piled up in the same table. Because rows
-- always flow strictly afschrift <- temp_afschrift <- temp_afschrift2
-- (enrichment drains temp_afschrift2 into temp_afschrift; migration
-- drains temp_afschrift into afschrift), "table, then that table's own
-- ID" reconstructs the correct global order — the three ID columns don't
-- need to relate to each other directly. See docs/ARCHITECTURE.md.
--
-- Params:
--   :rekening_text — raw account text as it appears in temp_afschrift2.Rekening
--   :rekening_id   — resolved Rekening.ID, or NULL if the account isn't
--                     linked yet (in which case afschrift/temp_afschrift
--                     contribute nothing — "col = NULL" matches no rows)

WITH sequence AS (
    SELECT ID, Datum, Naam, Bedrag_eur, Af_bij, Saldo_na_mutatie, 0 AS table_order
    FROM afschrift
    WHERE Rekening_ID = :rekening_id

    UNION ALL

    SELECT ID, Datum, Naam, Bedrag_eur, Af_bij, Saldo_na_mutatie, 1 AS table_order
    FROM temp_afschrift
    WHERE Rekening_ID = :rekening_id

    UNION ALL

    SELECT ID, Datum, Naam, Bedrag_eur, Af_bij, Saldo_na_mutatie, 2 AS table_order
    FROM temp_afschrift2
    WHERE Rekening = :rekening_text
),
checked AS (
    SELECT
        *,
        LAG(Saldo_na_mutatie) OVER (ORDER BY table_order, ID) AS prev_saldo
    FROM sequence
)
SELECT *
FROM checked
WHERE prev_saldo IS NOT NULL
  AND ROUND(
        CASE WHEN Af_bij = 'Bij' THEN prev_saldo + Bedrag_eur
             ELSE prev_saldo - Bedrag_eur
        END,
        2
      ) != ROUND(Saldo_na_mutatie, 2);
