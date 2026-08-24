-- Aggregate cross-check for one just-inserted upload batch, independent
-- of check_balance_chain.sql's row-by-row (LAG-based) link check: the
-- account's real prior balance (from confirmed history — afschrift —
-- and pending categorization — temp_afschrift) plus this batch's own
-- Bij total minus its Af total must land exactly on the batch's own
-- last reported Saldo_na_mutatie. Same underlying fact as the row-chain
-- check, verified a different way (one straight SUM instead of a
-- per-row LAG window) — a second, differently-computed line of defense
-- against the same class of problem (e.g. a missing/extra row, or a
-- wrong amount), at the cost of being unable to spot two individually-
-- broken links inside the same batch that happen to net to zero (an
-- inherent limit of any aggregate check — check_balance_chain.sql
-- already catches that case per-row, this one can't).
--
-- No prior history at all (this account's very first-ever upload) means
-- there's no independently-known "before" balance to check against —
-- this returns no rows in that case too (same as check_balance_chain.sql
-- exempting a first row that has no prev_saldo).
--
-- Run this AFTER inserting the new batch into temp_afschrift2, alongside
-- check_balance_chain.sql/check_dedup.sql in the same transaction —
-- roll back if it returns a row.
--
-- Params:
--   :rekening_text — raw account text as it appears in temp_afschrift2.Rekening
--   :rekening_id   — resolved Rekening.ID, or NULL if the account isn't linked yet

WITH history AS (
    SELECT Saldo_na_mutatie, 0 AS table_order, ID
    FROM afschrift
    WHERE Rekening_ID = :rekening_id

    UNION ALL

    SELECT Saldo_na_mutatie, 1 AS table_order, ID
    FROM temp_afschrift
    WHERE Rekening_ID = :rekening_id
),
prior_balance AS (
    SELECT Saldo_na_mutatie
    FROM history
    ORDER BY table_order DESC, ID DESC
    LIMIT 1
),
batch AS (
    SELECT ID, Bedrag_eur, Af_bij, Saldo_na_mutatie
    FROM temp_afschrift2
    WHERE Rekening = :rekening_text
),
batch_totals AS (
    SELECT
        COALESCE(SUM(CASE WHEN Af_bij = 'Bij' THEN Bedrag_eur ELSE 0 END), 0) AS bij_total,
        COALESCE(SUM(CASE WHEN Af_bij = 'Af' THEN Bedrag_eur ELSE 0 END), 0) AS af_total
    FROM batch
),
batch_end AS (
    SELECT Saldo_na_mutatie AS end_balance
    FROM batch
    ORDER BY ID DESC
    LIMIT 1
)
SELECT
    prior_balance.Saldo_na_mutatie AS initial_balance,
    batch_end.end_balance,
    batch_totals.bij_total,
    batch_totals.af_total,
    ROUND(batch_end.end_balance - prior_balance.Saldo_na_mutatie, 2) AS actual_diff,
    ROUND(batch_totals.bij_total - batch_totals.af_total, 2) AS expected_diff
FROM prior_balance, batch_end, batch_totals
WHERE ROUND(batch_end.end_balance - prior_balance.Saldo_na_mutatie, 2)
      != ROUND(batch_totals.bij_total - batch_totals.af_total, 2);
