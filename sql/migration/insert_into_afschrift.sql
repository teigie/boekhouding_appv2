-- Fase 4 migration: copies one account's fully-resolved temp_afschrift
-- backlog into the permanent afschrift ledger, preserving original row
-- order — afschrift.Saldo_na_mutatie is a running balance, so order is
-- load-bearing (see docs/ARCHITECTURE.md and sql/migration/README.md).
--
-- The caller MUST have already verified via count_unresolved.sql that
-- zero rows for this account are outside processed = 1 — this statement
-- doesn't re-check that itself, it only scopes to the account (and its
-- owner, defensively) and copies whatever's currently there.
--
-- Must run immediately followed by delete_from_temp_afschrift.sql for the
-- same account, inside the same transaction.
--
-- Params: :rekening_id, :user_id

INSERT INTO afschrift
    (Datum, Naam, Rekening_ID, Tegenrekening, Code, Af_bij, Bedrag_eur,
     Mutatiesoort_ID, Mededeling, Saldo_na_mutatie, Tag, Afschrift_cat_ID)
SELECT
    t.Datum, t.Naam, t.Rekening_ID, t.Tegenrekening, t.Code, t.Af_bij,
    t.Bedrag_eur, t.Mutatiesoort_ID, t.Mededeling, t.Saldo_na_mutatie,
    t.Tag, t.Afschrift_cat_ID
FROM temp_afschrift t
JOIN Rekening r ON r.ID = t.Rekening_ID
WHERE t.Rekening_ID = :rekening_id
  AND r.user_ID = :user_id
ORDER BY t.ID;
