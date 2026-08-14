-- Third categorization signal, structurally different from the two
-- keyword-based ones: a transaction is an "Interne overboeking" (internal
-- transfer) when its Tegenrekening is itself a Rekening linked to the
-- SAME user as the account being categorized — a transfer between two of
-- your own accounts, not a keyword match on Naam/Mededeling at all.
--
-- Relies on the "Interne overboeking" category existing under that exact
-- name (seeded by sql/seed_data.sql) — there's no dedicated schema flag
-- marking a category as "the internal-transfer one", and category rename
-- isn't supported by sql/queries/reference_data/ today, so this is safe
-- to rely on in practice. If the category is missing, this simply matches
-- nothing (JOIN finds no row) rather than erroring.
--
-- Standalone/reusable (e.g. to preview matches); categorize_batch.sql
-- embeds the same join itself rather than including this file, since
-- SQLite has no cross-file inclusion.
--
-- Params:
--   :rekening_text — raw account text as it appears in temp_afschrift2.Rekening
--   :user_id       — owning user of :rekening_text (see
--                     sql/queries/rekeningen/find_by_name.sql)

SELECT DISTINCT t.ID AS temp_id, ic.ID AS cat_ID
FROM temp_afschrift2 t
JOIN Rekening tegenrekening ON tegenrekening.name = t.Tegenrekening
JOIN afschrift_categorien ic ON ic.Name = 'Interne overboeking'
WHERE t.Rekening = :rekening_text
  AND tegenrekening.user_ID = :user_id;
