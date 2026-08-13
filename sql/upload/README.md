# Upload-gate queries

Runs at raw-upload time, inside the same DB transaction as the
`temp_afschrift2` insert — not part of enrichment (which resolves FKs and
categories on rows that already passed these gates).

- `check_balance_chain.sql` — per account, verifies the running balance
  has no break anywhere across confirmed history + pending enrichment +
  the newly-inserted batch.
- `check_dedup.sql` — per account, finds duplicate rows (by
  Datum+Bedrag_eur+Saldo_na_mutatie+Naam) across the same three sources.

Both run against the *already-inserted* new batch (insert first, then
check, inside one transaction): if either returns any rows, `ROLLBACK` —
nothing from this upload is kept. If both come back empty, `COMMIT`. This
mirrors the migration step's all-or-nothing-per-account rule, applied one
stage earlier: see docs/ARCHITECTURE.md.
