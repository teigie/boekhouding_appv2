-- Finds duplicate rows for an account: any (Datum, Bedrag_eur,
-- Saldo_na_mutatie, Naam) combination appearing more than once across
-- confirmed history (afschrift), pending categorization (temp_afschrift), and
-- the newly-uploaded batch (temp_afschrift2) combined. An empty result
-- means no duplicates.
--
-- Run this AFTER inserting the new batch into temp_afschrift2, inside the
-- same transaction as check_balance_chain.sql — roll back if either
-- returns any rows.
--
-- Date formats differ across tables (temp_afschrift2.Datum is the raw
-- "YYYYMMDD" from the bank file; temp_afschrift/afschrift.Datum is
-- "YYYY-MM-DD" once categorization has run), so temp_afschrift2's Datum is
-- normalized to "YYYY-MM-DD" here before comparing — otherwise the same
-- calendar date would never match across tables.
--
-- Params:
--   :rekening_text — raw account text as it appears in temp_afschrift2.Rekening
--   :rekening_id   — resolved Rekening.ID, or NULL if the account isn't linked yet

WITH sequence AS (
    SELECT Datum, Bedrag_eur, Saldo_na_mutatie, Naam
    FROM afschrift
    WHERE Rekening_ID = :rekening_id

    UNION ALL

    SELECT Datum, Bedrag_eur, Saldo_na_mutatie, Naam
    FROM temp_afschrift
    WHERE Rekening_ID = :rekening_id

    UNION ALL

    SELECT
        substr(Datum, 1, 4) || '-' || substr(Datum, 5, 2) || '-' || substr(Datum, 7, 2) AS Datum,
        Bedrag_eur, Saldo_na_mutatie, Naam
    FROM temp_afschrift2
    WHERE Rekening = :rekening_text
)
SELECT Datum, Bedrag_eur, Saldo_na_mutatie, Naam, COUNT(*) AS occurrences
FROM sequence
GROUP BY Datum, Bedrag_eur, Saldo_na_mutatie, Naam
HAVING COUNT(*) > 1;
