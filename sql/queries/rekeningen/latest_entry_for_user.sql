-- The single most recent statement for one account — from temp_afschrift
-- if it has any pending rows at all, otherwise from afschrift. Shown
-- next to the account on the profile page (app/user_page.py) so a user
-- can see at a glance what the latest known transaction is, without
-- having to go look on /review or the dashboard.
--
-- Never compares Datum across the two tables to decide which is
-- "newer": per docs/ARCHITECTURE.md, temp_afschrift's entire backlog for
-- an account is always strictly newer than whatever has already been
-- migrated into afschrift (migration is all-or-nothing and only ever
-- runs once every row for that account is resolved) — so if
-- temp_afschrift has ANY row for this account, its own latest row
-- (highest ID) is unconditionally the account's true latest statement;
-- afschrift isn't even consulted in that case. `bron` tells the caller
-- which table it came from, so the page can flag a not-yet-migrated
-- entry as such.
--
-- Params: :rekening_id, :user_id

SELECT bron, Datum, Naam, Af_bij, Bedrag_eur, Mededeling
FROM (
    SELECT 'temp_afschrift' AS bron, ID, Datum, Naam, Af_bij, Bedrag_eur, Mededeling, 1 AS prioriteit
    FROM temp_afschrift
    WHERE Rekening_ID = :rekening_id
      AND Rekening_ID IN (SELECT ID FROM Rekening WHERE user_ID = :user_id)
    UNION ALL
    SELECT 'afschrift' AS bron, ID, Datum, Naam, Af_bij, Bedrag_eur, Mededeling, 0 AS prioriteit
    FROM afschrift
    WHERE Rekening_ID = :rekening_id
      AND Rekening_ID IN (SELECT ID FROM Rekening WHERE user_ID = :user_id)
)
ORDER BY prioriteit DESC, ID DESC
LIMIT 1;
