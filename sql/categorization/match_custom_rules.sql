-- Rule-based categorization: every one of the categorizing user's own
-- rules (afschrift_cat_regels) is checked against one account's pending
-- temp_afschrift2 backlog. A category matches if AT LEAST ONE of its
-- rules matches (OR across a category's rules — see
-- app/categorization_rules.py and sql/schema.sql for the model).
--
-- A rule is a set of per-column conditions (afschrift_cat_regel_kolommen)
-- — a column simply absent from a rule is never checked. ALL columns a
-- rule DOES have must match for the rule itself to match (AND across
-- columns; the EXISTS guard below additionally requires at least one
-- column, since a rule with zero conditions would otherwise vacuously
-- match every row).
--
-- Each column-condition has one or more keywords
-- (afschrift_cat_regel_keywords) plus its own combine_mode:
--   'OR'  — the column matches if ANY of its keywords match the row
--   'AND' — the column matches if ALL of its keywords match the row
-- Implemented below as: for each (rule, column) group, count how many of
-- its keywords match; the group FAILS if that count is < 1 (OR mode) or
-- < the total keyword count (AND mode). A rule matches iff NO group
-- attached to it fails.
--
-- Matching per column, by type:
--   Naam, Tegenrekening, Mededeling, Tag, Mutatiesoort — substring (LIKE)
--   Code, Af_bij                                        — exact text match
--   Bedrag_eur, Saldo_na_mutatie                         — exact NUMERIC
--     match via CAST(... AS REAL), not text comparison, so '25' and
--     '25.00' are the same value. app/categorization_rules.py parses
--     Dutch-formatted user input ('1.234,56': '.' thousands, ','
--     decimals) into this canonical numeric form before it's stored.
--
-- Standalone/reusable (e.g. to preview matches); categorize_batch.sql
-- embeds the same logic itself rather than including this file, since
-- SQLite has no cross-file inclusion.
--
-- Params:
--   :rekening_text — raw account text as it appears in temp_afschrift2.Rekening
--   :user_id       — owning user of :rekening_text — scopes which rules
--                     can match, since rules are per-user

SELECT DISTINCT t.ID AS temp_id, r.cat_ID
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
      GROUP BY gk.ID, gk.combine_mode
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
        CASE WHEN gk.combine_mode = 'AND' THEN COUNT(*) ELSE 1 END
  );
