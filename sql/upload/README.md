# Upload-gate queries

Post-insert continuity checks, run at raw-upload time inside the same DB
transaction as the `temp_afschrift2` insert. These need the newly-inserted
batch already present, since they check it against the account's existing
history — see docs/ARCHITECTURE.md for why that means they can't run
before the insert.

(The other kind of upload gate — pre-insert FK checks for Rekening and
Mutatiesoort — runs *before* any insert, using point lookups
(`sql/queries/rekeningen/find_by_name.sql`,
`sql/queries/mutatiesoorten/find_by_name.sql`) directly from
`app/upload.py`, not from a file in this folder.)

- `check_balance_chain.sql` — per account, verifies the running balance
  has no break anywhere across confirmed history + pending categorization +
  the newly-inserted batch.
- `check_dedup.sql` — per account, finds duplicate rows (by
  Datum+Bedrag_eur+Saldo_na_mutatie+Naam) across the same three sources.

Both run against the *already-inserted* new batch (insert first, then
check, inside one transaction): if either returns any rows, `ROLLBACK` —
nothing from this upload is kept. If both come back empty, `COMMIT`. This
mirrors the migration step's all-or-nothing-per-account rule, applied one
stage earlier: see docs/ARCHITECTURE.md.
