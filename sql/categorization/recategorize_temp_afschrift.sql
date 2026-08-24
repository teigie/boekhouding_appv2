-- Re-runs rule-based categorization against ALL of one user's current
-- temp_afschrift rows (any processed value), across all of that user's
-- accounts at once. Triggered on demand (the "Categorisatie opnieuw
-- proberen" button on /upload) after the user adds/edits rules, so:
--   - rows that didn't match anything at upload time get a fresh chance,
--   - rows that already resolved to exactly one category get re-checked
--     too, in case a newly-added rule now ALSO matches them — surfacing
--     that conflict as ambiguous (processed = 2) instead of silently
--     leaving the earlier, now-questionable single answer in place.
--
-- processed = 1 is set identically whether a row was resolved
-- automatically or picked by hand on /review — there's no separate flag
-- to tell those apart (see sql/queries/temp_afschrift/set_category.sql).
-- So an already-resolved row is only ever PROMOTED to ambiguous (a new
-- rule conflicts with it) here — it is never demoted back to unresolved
-- just because zero rules currently match it (that's the normal case for
-- anything picked by hand), and its category is never silently swapped
-- for a different single match. Only rows that were already 0 or 2 before
-- are free to move to whatever the fresh match outcome implies.
--
-- Matching logic mirrors match_custom_rules.sql exactly, with one
-- necessary adaptation: temp_afschrift2's raw Mutatiesoort text no longer
-- exists once a row has moved into temp_afschrift (only Mutatiesoort_ID
-- remains), so a rule's 'Mutatiesoort' condition is instead checked
-- against ANY raw label in mutatiesoort_mapping that resolves to this
-- row's same Mutatiesoort_ID — equivalent in spirit, since that mapping
-- already canonicalizes synonymous raw labels into one mutatiesoort.
--
-- Afschrift_subcat_ID follows the same "only ever promoted, never
-- silently overwritten" rule as Afschrift_cat_ID above: an already
-- resolved row keeps its existing subcategory (manual or automatic)
-- unless it gets promoted to ambiguous, in which case both are cleared.
-- A row newly resolved here gets a subcategory only if the rule(s)
-- matching its winning category agree on one (see categorize_batch.sql's
-- subcat_summary for the exact same "agree, or leave NULL" logic).
--
-- Params:
--   :user_id — only rows on this user's own Rekeningen are considered,
--              matched only against this user's own rules
--
-- Returns (ID, processed) for every row whose processed/Afschrift_cat_ID/
-- Afschrift_subcat_ID actually changed, so the caller can tally the
-- outcome without a second query. A row that ends up in the exact same
-- state it started in is never touched (and never appears in the
-- result).

WITH scope AS (
    SELECT
        t.ID, t.processed AS old_processed, t.Afschrift_cat_ID AS old_cat_id,
        t.Afschrift_subcat_ID AS old_subcat_id
    FROM temp_afschrift t
    JOIN Rekening rk ON rk.ID = t.Rekening_ID
    WHERE rk.user_ID = :user_id
),
rule_matches AS (
    SELECT DISTINCT t.ID AS temp_id, r.cat_ID, r.subcat_ID
    FROM temp_afschrift t
    JOIN scope s ON s.ID = t.ID
    JOIN afschrift_cat_regels r ON r.user_ID = :user_id
    WHERE EXISTS (
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
              WHEN gk.kolom = 'Mutatiesoort'      AND EXISTS (
                                                          SELECT 1 FROM mutatiesoort_mapping mm
                                                          WHERE mm.mutatiesoort_ID = t.Mutatiesoort_ID
                                                            AND mm.Name LIKE '%' || k.keyword || '%'
                                                        )                                                       THEN 1
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
    -- See categorize_batch.sql's identical CTE — per (temp_id, cat_ID),
    -- how many DISTINCT non-NULL subcat_ID's the matching rules disagree
    -- on. Only ever consulted below for a row's winning category.
    SELECT temp_id, cat_ID, COUNT(DISTINCT subcat_ID) AS subcat_variety, MIN(subcat_ID) AS single_subcat_ID
    FROM rule_matches
    GROUP BY temp_id, cat_ID
),
resolution AS (
    SELECT
        s.ID AS temp_id,
        s.old_processed,
        s.old_cat_id,
        s.old_subcat_id,
        CASE
            WHEN s.old_processed = 1 AND COALESCE(ms.match_count, 0) >= 2 THEN 2
            WHEN s.old_processed = 1 THEN s.old_processed
            WHEN ms.match_count IS NULL OR ms.match_count = 0 THEN 0
            WHEN ms.match_count = 1 THEN 1
            ELSE 2
        END AS new_processed,
        CASE
            WHEN s.old_processed = 1 AND COALESCE(ms.match_count, 0) >= 2 THEN NULL
            WHEN s.old_processed = 1 THEN s.old_cat_id
            WHEN ms.match_count = 1 THEN ms.single_cat_ID
            ELSE NULL
        END AS new_cat_id,
        CASE
            WHEN s.old_processed = 1 AND COALESCE(ms.match_count, 0) >= 2 THEN NULL
            WHEN s.old_processed = 1 THEN s.old_subcat_id
            WHEN ms.match_count = 1 AND COALESCE(ss.subcat_variety, 0) <= 1 THEN ss.single_subcat_ID
            ELSE NULL
        END AS new_subcat_id
    FROM scope s
    LEFT JOIN match_summary ms ON ms.temp_id = s.ID
    LEFT JOIN subcat_summary ss ON ss.temp_id = s.ID AND ss.cat_ID = ms.single_cat_ID
)
UPDATE temp_afschrift
SET
    Afschrift_cat_ID = (SELECT new_cat_id FROM resolution WHERE resolution.temp_id = temp_afschrift.ID),
    Afschrift_subcat_ID = (SELECT new_subcat_id FROM resolution WHERE resolution.temp_id = temp_afschrift.ID),
    processed = (SELECT new_processed FROM resolution WHERE resolution.temp_id = temp_afschrift.ID)
WHERE ID IN (
    SELECT temp_id FROM resolution
    WHERE new_processed IS NOT old_processed
       OR new_cat_id IS NOT old_cat_id
       OR new_subcat_id IS NOT old_subcat_id
)
RETURNING ID, processed;
