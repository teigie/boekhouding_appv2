-- Categorizes one account's entire pending temp_afschrift2 backlog in one
-- atomic run: resolves Mutatiesoort_ID, combines all category-match
-- signals into `processed`, and inserts the result into temp_afschrift in
-- one INSERT ... SELECT, preserving temp_afschrift2's row order (see
-- docs/ARCHITECTURE.md for why order is load-bearing).
--
-- Rekening_ID/Mutatiesoort_ID resolution is independent of `processed` —
-- both are expected to always resolve (Rekening was already validated at
-- upload time; mutatiesoort_mapping is structural reference data — an
-- unmatched Mutatiesoort fails the NOT NULL constraint below rather than
-- being silently treated as "unresolved"). `processed` reflects only the
-- combined category-match outcome, from three independent signals (see
-- sql/categorization/README.md for each):
--   - Naam vs. afschrift_cat_keywords ("simple")
--   - Mededeling vs. afschrift_cat_mededeling_keywords ("difficult")
--   - Tegenrekening resolving to another account of the SAME user ->
--     "Interne overboeking" (match_internal_transfer.sql)
--
-- Current combination strategy (not final, expected to change — see
-- sql/categorization/README.md): all three are always checked, and the
-- categories matched from each are unioned into one set per row:
--   0 = no category matched (none of the three) — needs a manual category
--   1 = exactly one category matched — eligible for migration
--   2 = more than one category matched — ambiguous, needs a manual pick
--
-- Must run against an account's FULL current temp_afschrift2 backlog,
-- immediately followed by clear_temp_afschrift2.sql for the same account,
-- inside the same transaction — never a partial subset.
--
-- Returns `processed` for every inserted row, so the caller can tally
-- resolved/unresolved/ambiguous counts without a separate query.
--
-- Params:
--   :rekening_text — raw account text as it appears in temp_afschrift2.Rekening
--   :rekening_id   — resolved Rekening.ID (see sql/queries/rekeningen/find_by_name.sql)
--   :user_id       — owning user of :rekening_text/:rekening_id

WITH naam_matches AS (
    SELECT DISTINCT t.ID AS temp_id, k.cat_ID
    FROM temp_afschrift2 t
    JOIN afschrift_cat_keywords k
        ON t.Naam LIKE '%' || k.keyword || '%'
    WHERE t.Rekening = :rekening_text
),
mededeling_matches AS (
    SELECT DISTINCT t.ID AS temp_id, k.cat_ID
    FROM temp_afschrift2 t
    JOIN afschrift_cat_mededeling_keywords k
        ON t.Mededeling LIKE '%' || k.keyword || '%'
    WHERE t.Rekening = :rekening_text
),
internal_transfer_matches AS (
    SELECT DISTINCT t.ID AS temp_id, ic.ID AS cat_ID
    FROM temp_afschrift2 t
    JOIN Rekening tegenrekening ON tegenrekening.name = t.Tegenrekening
    JOIN afschrift_categorien ic ON ic.Name = 'Interne overboeking'
    WHERE t.Rekening = :rekening_text
      AND tegenrekening.user_ID = :user_id
),
combined_matches AS (
    SELECT temp_id, cat_ID FROM naam_matches
    UNION
    SELECT temp_id, cat_ID FROM mededeling_matches
    UNION
    SELECT temp_id, cat_ID FROM internal_transfer_matches
),
match_summary AS (
    SELECT temp_id, COUNT(*) AS match_count, MIN(cat_ID) AS single_cat_ID
    FROM combined_matches
    GROUP BY temp_id
)
INSERT INTO temp_afschrift
    (Datum, Naam, Rekening_ID, Tegenrekening, Code, Af_bij, Bedrag_eur,
     Mutatiesoort_ID, Mededeling, Saldo_na_mutatie, Tag, Afschrift_cat_ID, processed)
SELECT
    substr(t.Datum, 1, 4) || '-' || substr(t.Datum, 5, 2) || '-' || substr(t.Datum, 7, 2),
    t.Naam,
    :rekening_id,
    t.Tegenrekening,
    t.Code,
    t.Af_bij,
    t.Bedrag_eur,
    mm.mutatiesoort_ID,
    t.Mededeling,
    t.Saldo_na_mutatie,
    t.Tag,
    CASE WHEN ms.match_count = 1 THEN ms.single_cat_ID ELSE NULL END,
    CASE
        WHEN ms.match_count IS NULL OR ms.match_count = 0 THEN 0
        WHEN ms.match_count = 1 THEN 1
        ELSE 2
    END
FROM temp_afschrift2 t
LEFT JOIN mutatiesoort_mapping mm ON mm.Name = t.Mutatiesoort
LEFT JOIN match_summary ms ON ms.temp_id = t.ID
WHERE t.Rekening = :rekening_text
ORDER BY t.ID
RETURNING processed;
