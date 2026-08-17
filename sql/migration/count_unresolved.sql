-- Guard for insert_into_afschrift.sql: counts how many temp_afschrift rows
-- for the given account are NOT (yet) processed = 1 — i.e. still
-- unresolved (0) or ambiguous (2). Migration must refuse to run unless
-- this is zero — see sql/migration/README.md and
-- docs/ARCHITECTURE.md's Fase 4.
--
-- Scoped through Rekening.user_ID defensively, same style as
-- sql/queries/temp_afschrift/set_category.sql — the caller should have
-- already verified ownership of :rekening_id, but a stale/guessed ID
-- must still count as "not this user's rows to migrate", not leak a
-- count from another user's account.
--
-- Params: :rekening_id, :user_id

SELECT COUNT(*) AS unresolved
FROM temp_afschrift t
JOIN Rekening r ON r.ID = t.Rekening_ID
WHERE t.Rekening_ID = :rekening_id
  AND r.user_ID = :user_id
  AND t.processed != 1;
