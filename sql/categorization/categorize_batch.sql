-- Categorizes one account's entire pending temp_afschrift2 backlog in one
-- atomic run: resolves Mutatiesoort_ID, evaluates every one of the
-- categorizing user's own rules against every row, and inserts the
-- result into temp_afschrift in one INSERT ... SELECT, preserving
-- temp_afschrift2's row order (see docs/ARCHITECTURE.md for why order is
-- load-bearing).
--
-- Rekening_ID/Mutatiesoort_ID resolution is independent of `processed` —
-- both are expected to always resolve (Rekening was already validated at
-- upload time; mutatiesoort_mapping is structural reference data — an
-- unmatched Mutatiesoort fails the NOT NULL constraint below rather than
-- being silently treated as "unresolved"). `processed` reflects only the
-- rule-match outcome — see sql/categorization/README.md and
-- match_custom_rules.sql (embedded below) for the full matching
-- semantics: AND across a rule's own columns, AND across a column's own
-- keywords, OR across a category's rules.
--
-- Current combination strategy (not final, expected to change — see
-- sql/categorization/README.md):
--   0 = no rule matched — needs a manual category
--   1 = exactly one category matched (by one or more of its rules) — eligible for migration
--   2 = more than one category matched — ambiguous, needs a manual pick
-- This is based ONLY on distinct cat_ID — entirely unchanged by
-- subcategories below.
--
-- Afschrift_subcat_ID is resolved separately and never affects the above:
-- among the rule(s) that matched the winning category, if they agree on
-- one subcategory (or only one of them sets one — NULLs are ignored) it's
-- assigned; if they genuinely disagree (2+ different non-NULL
-- subcat_ID's), it's simply left NULL rather than making the row
-- ambiguous — subcategory is always optional/best-effort, never blocking
-- (see sql/schema.sql).
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

WITH rule_matches AS (
    -- See sql/categorization/match_custom_rules.sql for the standalone,
    -- documented copy of this exact logic.
    SELECT DISTINCT t.ID AS temp_id, r.cat_ID, r.subcat_ID
    FROM temp_afschrift2 t
    JOIN afschrift_cat_regels r ON r.user_ID = :user_id
    WHERE t.Rekening = :rekening_text
      AND EXISTS (
          SELECT 1 FROM afschrift_cat_regel_kolommen gk WHERE gk.regel_ID = r.ID
      )
      AND NOT EXISTS (
          SELECT gk.ID
          FROM afschrift_cat_regel_kolommen gk
          JOIN afschrift_cat_regel_keywords k ON k.regel_kolom_ID = gk.ID
          WHERE gk.regel_ID = r.ID
          GROUP BY gk.ID
          HAVING
            SUM(
              CASE
                WHEN gk.kolom = 'Naam'             AND t.Naam                            LIKE '%' || k.keyword || '%' THEN 1
                WHEN gk.kolom = 'Tegenrekening'     AND t.Tegenrekening                   LIKE '%' || k.keyword || '%' THEN 1
                WHEN gk.kolom = 'Mededeling'        AND t.Mededeling                      LIKE '%' || k.keyword || '%' THEN 1
                WHEN gk.kolom = 'Tag'               AND t.Tag                             LIKE '%' || k.keyword || '%' THEN 1
                WHEN gk.kolom = 'Mutatiesoort'      AND t.Mutatiesoort                    LIKE '%' || k.keyword || '%' THEN 1
                WHEN gk.kolom = 'Code'              AND t.Code                            =    k.keyword               THEN 1
                WHEN gk.kolom = 'Af_bij'            AND t.Af_bij                          =    k.keyword               THEN 1
                WHEN gk.kolom = 'Bedrag_eur'        AND CAST(t.Bedrag_eur AS REAL)        =    CAST(k.keyword AS REAL) THEN 1
                WHEN gk.kolom = 'Saldo_na_mutatie'  AND CAST(t.Saldo_na_mutatie AS REAL)  =    CAST(k.keyword AS REAL) THEN 1
                ELSE 0
              END
            )
            <
            COUNT(*)
      )
),
match_summary AS (
    SELECT temp_id, COUNT(DISTINCT cat_ID) AS match_count, MIN(cat_ID) AS single_cat_ID
    FROM rule_matches
    GROUP BY temp_id
),
subcat_summary AS (
    -- Per (temp_id, cat_ID): how many DISTINCT non-NULL subcat_ID's did
    -- the rules matching that category disagree on. Only ever consulted
    -- below for the row's single winning category (match_count = 1).
    SELECT temp_id, cat_ID, COUNT(DISTINCT subcat_ID) AS subcat_variety, MIN(subcat_ID) AS single_subcat_ID
    FROM rule_matches
    GROUP BY temp_id, cat_ID
)
INSERT INTO temp_afschrift
    (Datum, Naam, Rekening_ID, Tegenrekening, Code, Af_bij, Bedrag_eur,
     Mutatiesoort_ID, Mededeling, Saldo_na_mutatie, Tag, Afschrift_cat_ID, Afschrift_subcat_ID, processed)
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
    CASE WHEN ms.match_count = 1 AND ss.subcat_variety <= 1 THEN ss.single_subcat_ID ELSE NULL END,
    CASE
        WHEN ms.match_count IS NULL OR ms.match_count = 0 THEN 0
        WHEN ms.match_count = 1 THEN 1
        ELSE 2
    END
FROM temp_afschrift2 t
LEFT JOIN mutatiesoort_mapping mm ON mm.Name = t.Mutatiesoort
LEFT JOIN match_summary ms ON ms.temp_id = t.ID
LEFT JOIN subcat_summary ss ON ss.temp_id = t.ID AND ss.cat_ID = ms.single_cat_ID
WHERE t.Rekening = :rekening_text
ORDER BY t.ID
RETURNING processed;
