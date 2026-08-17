-- Third categorization signal, structurally different from the two
-- keyword-based ones: a transaction is an "Interne overboeking" (internal
-- transfer) when its Tegenrekening is itself a Rekening linked to the
-- SAME user as the account being categorized — a transfer between two of
-- your own accounts, not a keyword match on Naam/Mededeling at all.
--
-- Relies on the "Interne overboeking" category existing under that exact
-- name FOR THAT USER (categories are per-user) — there's no dedicated
-- schema flag marking a category as "the internal-transfer one", and
-- category rename isn't supported by sql/queries/reference_data/ today,
-- so this is safe to rely on in practice. A user who hasn't added that
-- category yet (e.g. a brand-new user) simply matches nothing here rather
-- than erroring — see sql/categorization/README.md.
--
-- Standalone/reusable (e.g. to preview matches); categorize_batch.sql
-- embeds the same join itself rather than including this file, since
-- SQLite has no cross-file inclusion.
--
-- Params:
--   :rekening_text — raw account text as it appears in temp_afschrift2.Rekening
--   :user_id       — owning user of :rekening_text/:rekening_id — scopes
--                     both which Rekening counts as "one of your own" and
--                     which category counts as "your Interne overboeking"

SELECT DISTINCT t.ID AS temp_id, ic.ID AS cat_ID
FROM temp_afschrift2 t
JOIN Rekening tegenrekening ON tegenrekening.name = t.Tegenrekening
JOIN afschrift_categorien ic ON ic.Name = 'Interne overboeking' AND ic.user_ID = :user_id
WHERE t.Rekening = :rekening_text
  AND tegenrekening.user_ID = :user_id;
